#!/usr/bin/env python
from google.cloud import datastore as ds
import npyscreen as nps
import os
import sys
import uuid

VERSION = 'A'

class VarStore(object):
    def __init__(self):
        self.dsc = ds.Client()
        self.transaction = self.dsc.transaction()
        self.transaction.begin()
        q = self.dsc.query(kind='ENV_VAR')
        self.vars = { i['VAR_NAME'] : i
                for i in list(q.fetch())}

    def getVarsList(self):
        return list(self.vars.keys())
    

    def updateVar(self, name, value, description):
        self.vars[name]['VAR_VALUE'] = value
        self.vars[name]['VAR_DESC'] = description
        self.transaction.put(self.vars[name])

    def createVar(self):
        name = uuid.uuid4().hex 
        ekey = self.dsc.key('ENV_VAR', name)
        new = ds.Entity(key=ekey)
        new['VAR_NAME'] = name
        new['VAR_DESC'] = 'describe the variable here'
        self.transaction.put(new)
        self.vars[name] = new

    def deleteVar(self, name):
        self.transaction.delete(self.vars[name].key)
        del self.vars[name]

    def commit(self):
        self.transaction.commit()


class Cconfigr(nps.NPSAppManaged):
    def onStart(self):
        self.vdb = VarStore()

        self.forms = {
                'MAIN' : MainForm,
                'AUTH' : AuthForm
                }

        for k,v in self.forms.items():
            self.addForm(
                    k, v,
                    name = 'cconfigr v{}'\
                            .format(VERSION))
            
class AuthForm(nps.ActionFormMinimal):

    def create(self):
        self.text = self.add(
                nps.TitleFixedText,
                name='ENV VAR MANAGER',
                value='you need to set GOOGLE_APPLICATION_CREDENTIALS')

    def on_ok(self):
        sys.exit(0)

class MainForm(nps.ActionFormMinimal):

    def create(self):
        self.vmenu = self.add(VarMenuWidget,
                values=self.parentApp.vdb.getVarsList(), max_height=10)
        self.name = self.add(nps.TitleText,
                name='NAME',value='')
        self.val = self.add(nps.TitleText,
                name='VALUE',value='')
        self.desc = self.add(nps.TitleText,
                name='DESCRIPTION',value='')
        self.save = self.add(SaveVarBtn, value='SAVE')
        
        return

    def on_ok(self):
        self.parentApp.vdb.commit()
        sys.exit(0)


    def update_list(self):
        self.vmenu.values = self.parentApp.vdb.getVarsList()
        self.vmenu.display()

    def update_info(self):
        print(self.curr)
        self.name.value = 'TOUCHED'
        self.desc.value = 'TOUCHED'
        self.display()
        
class VarMenuWidget(nps.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(VarMenuWidget, self).__init__(*args, **keywords)
        self.add_handlers({
            '^A': self.addVar,
            '^D': self.delVar
            })


    def actionHighLighted(self, act_on_this, keypress):
        self.selectVar()

    def selectVar(self, *args, **keywords):
        self.parent.name = self.values[self.cursor_line]
        self.parent.update_info()

    def addVar(self, *args, **keywords):
        self.parent.parentApp.vdb.createVar()
        self.parent.update_list()

    def delVar(self, *args, **keywords):
        self.parent.parentApp.vdb.deleteVar(self.values[self.cursor_line])
        self.parent.update_list()

class SaveVarBtn(nps.ButtonPress):

    def whenPressed(self):
        self.parent.parentApp.vdb.updateVar(
                self.parent.name,
                self.parent.val,
                self.parent.desc)

        
if __name__ == '__main__':
    app = Cconfigr()
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        app.STARTING_FORM = 'AUTH'
    app.run()
