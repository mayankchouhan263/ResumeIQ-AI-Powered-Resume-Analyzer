"""Pure-Python file-type sniffing.

Replaces python-magic/libmagic, which needs a native DLL/shared library and is the
cause of "failed to find libmagic" on Windows and on many hosting platforms.
"""
import io
import zipfile

PDF_MIME  = 'application/pdf'
DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
DOC_MIME  = 'application/msword'


def detect_mime(data: bytes) -> str:
    head = data[:1024]

    if b'%PDF-' in head:
        return PDF_MIME

    if data[:2] == b'PK':                       # zip container -> maybe DOCX
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
            if '[Content_Types].xml' in names and any(n.startswith('word/') for n in names):
                return DOCX_MIME
        except zipfile.BadZipFile:
            pass
        return 'application/zip'

    if data[:8] == bytes.fromhex('D0CF11E0A1B11AE1'):   # legacy OLE2 (.doc)
        return DOC_MIME

    return 'application/octet-stream'
