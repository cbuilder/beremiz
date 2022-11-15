""" This test opens, modifies, builds and runs exemple project named "python".
Test succeeds if runtime's stdout behaves as expected
"""

import os
import time

# allow module import from current test directory's parent
addImportPath(os.path.dirname(getBundlePath()))

# common test definitions module
from sikuliberemiz import run_test, AuxiliaryProcess

def test(app):

    server = AuxiliaryProcess(app, ["/bin/bash",os.path.join(getBundlePath(),"opcua_service.bash")])
    #server = AuxiliaryProcess(app, ["/bin/bash","-c","echo $PWD"])

    app.doubleClick("opcua_node.png")

    app.WaitIdleUI()

    # app.click("Browse Server") # OCR didn't work because of gradient in button...
    app.click("opcua_browse_server.png")

    app.WaitIdleUI()

    app.doubleClick("Objects")

    app.WaitIdleUI()

    app.doubleClick("TestObject")

    app.dragNdrop("TestIn", "output variables")

    app.wait(1)

    app.dragNdrop("TestOut", "input variables")

    app.wait(3)

    app.k.Clean()

    app.waitForChangeAndIdleStdout()

    app.k.Build()

    app.waitForChangeAndIdleStdout()

    app.k.Connect()

    app.waitForChangeAndIdleStdout()

    app.k.Transfer()

    app.waitForChangeAndIdleStdout()

    app.k.Run()

    # wait 10 seconds for 10 patterns
    res = app.waitPatternInStdout("6.8", 10)

    server.close()

    return res

run_test(test, testproject="opcua_browse")