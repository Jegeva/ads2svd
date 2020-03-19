from java.io import File

def makeTempFile(prefix, suffix):
    '''Make a temporary file which is cleaned up on process exit'''
    # Can't use tempfile.NamedTemporaryFile() because Jython 2.5 deletes
    # it when it's closed (will be optional from 2.6 onwards).
    # For now, do it in Java.
    jtmp = File.createTempFile(prefix, suffix)
    jtmp.deleteOnExit()
    return jtmp.getCanonicalPath();

