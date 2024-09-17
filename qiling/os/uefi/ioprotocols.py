from binascii import crc32

from qiling.const import QL_ENDIAN
from qiling.os.const import *
from qiling.os.uefi import guids_db
from qiling.os.uefi.UefiSpec import EFI_SIMPLE_TEXT_INPUT_PROTOCOL, EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL
from qiling.os.uefi.const import *
from qiling.os.uefi.fncc import dxeapi
from qiling.os.uefi.utils import *
from qiling.os.uefi.ProcessorBind import *
from qiling.os.uefi.UefiSpec import *
from qiling.os.uefi.protocols import common


def initialize_Input_Protocol(ql: Qiling, gIP: int):
    descriptor = {
        'struct' : EFI_SIMPLE_TEXT_INPUT_PROTOCOL,
        'fields' : (
            ('Reset',               hook_Input_Reset),
            ('ReadKeyStroke',       hook_Read_Key_Stroke),
            ('WaitForKey',          hook_EFI_Event)
        )
    }

    ql.os.monotonic_count = 0
    instance = init_struct(ql, gIP, descriptor)
    instance.saveTo(ql, gIP)

def initialize_Output_Protocol(ql: Qiling, gOP: int):
    descriptor = {
        'struct' : EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL,
        'fields' : (
            ('Reset',               hook_Text_Reset),
            
            ('OutputString',        hook_Output_String),
            ('TestString',          hook_Test_String),
            
            ('QueryMode',           hook_Query_Mode),
            ('SetMode',             hook_Set_Mode),
            ('SetAttribute',        hook_Set_Attribute),
            
            ('ClearScreen',         hook_Clear_Screen),
            ('SetCursorPosition',   hook_Set_Cursor_Position),
            ('EnableCursor',        hook_Enable_Cursor),
            ('Mode')
        )
    }

    ql.os.monotonic_count = 0
    instance = init_struct(ql, gOP, descriptor)
    instance.saveTo(ql, gOP)