"""Local synthetic BIFF12 smoke coverage; no solutions to evaluation tasks."""
import io
import struct
from zipfile import ZipFile

from pyxlsb import biff12, open_workbook
from pyxlsb.reader import BIFF12Reader, RecordReader
from pyxlsb.worksheet import Worksheet


def record(identifier, data=b''):
    code=identifier.to_bytes(max(1,(identifier.bit_length()+7)//8), 'little')
    size=len(data); lengths=bytearray()
    while size>=128:
        lengths.append((size&127)|128); size>>=7
    return code+bytes(lengths)+bytes([size])+data


def string(text):
    raw=text.encode('utf-16le')
    return struct.pack('<I',len(raw)//2)+raw


def sheet_data():
    return b''.join([
        record(biff12.DIMENSION,struct.pack('<IIII',0,1,0,1)),
        record(biff12.SHEETDATA),
        record(biff12.ROW,struct.pack('<I',0)),
        record(biff12.FLOAT,struct.pack('<IId',0,0,12.5)),
        record(biff12.BOOL,struct.pack('<II?',1,0,True)),
        record(biff12.ROW,struct.pack('<I',1)),
        record(biff12.FORMULA_STRING,struct.pack('<II',0,0)+string('北京')),
        record(biff12.SHEETDATA_END),
    ])


def test_record_numbers_and_unicode():
    with RecordReader(struct.pack('<I',7)+string('日志')) as reader:
        assert reader.read_int()==7
        assert reader.read_string()=='日志'


def test_biff_record_dispatch():
    rows=list(BIFF12Reader(io.BytesIO(record(biff12.ROW,struct.pack('<I',4)))))
    assert rows[0][1].r==4


def test_rows_and_coordinates():
    with Worksheet('sample',io.BytesIO(sheet_data())) as sheet:
        rows=list(sheet.rows())
        assert [[c.v for c in row] for row in rows]==[[12.5,True],['北京',None]]
        assert rows[1][0].r==1


def test_zip_workbook_public_read(tmp_path):
    path=tmp_path/'sample.xlsb'
    with ZipFile(path,'w') as zf:
        zf.writestr('xl/_rels/workbook.bin.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.bin"/></Relationships>')
        zf.writestr('xl/workbook.bin',record(biff12.SHEET,b'\x00'*4+struct.pack('<I',1)+string('rId1')+string('数据'))+record(biff12.SHEETS_END))
        zf.writestr('xl/worksheets/sheet1.bin',sheet_data())
    with open_workbook(str(path)) as book:
        assert book.sheets==['数据']
        with book.get_sheet('数据') as sheet:
            assert list(sheet.rows())[0][0].v==12.5


if __name__=='__main__':
    from pathlib import Path
    from tempfile import TemporaryDirectory
    test_record_numbers_and_unicode()
    test_biff_record_dispatch()
    test_rows_and_coordinates()
    with TemporaryDirectory() as temporary:
        test_zip_workbook_public_read(Path(temporary))
    print('4 passed: primitives, BIFF dispatch, worksheet coordinates, ZIP workbook')
