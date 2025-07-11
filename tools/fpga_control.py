import ctypes
import math
import os


class FPGAControl:
    adc_ranges = {"12.5": (0, 0), "50.0": (0, 1), "100.0": (1, 0), "150.0": (1, 1)}
    bit_rates = {10: 0, 20: 1}

    int16_t = ctypes.c_int16
    int32_t = ctypes.c_int32
    uint32_t = ctypes.c_uint32
    BYTE = ctypes.c_ubyte
    WINAPI = ctypes.WINFUNCTYPE

    XferINTDataIn_type = WINAPI(
        int16_t,
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int32_t),
    )
    XferINTDataOut_type = WINAPI(
        int16_t,
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int16_t),
    )
    WriteFPGARegsC_type = WINAPI(
        int32_t,
        ctypes.POINTER(int16_t),
        ctypes.POINTER(int32_t),
        ctypes.POINTER(int32_t),
        ctypes.POINTER(int32_t),
        ctypes.POINTER(int32_t),
    )
    FastAllDataCap_type = WINAPI(
        int32_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        int32_t,
        int32_t,
        int32_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(int32_t),
    )

    def __init__(
        self,
        CONV_LOW_INT,
        CONV_HIGH_INT,
        CONV_CONFIG,
        CLK_HIGH,
        CLK_LOW,
        DDC_CLK_CONFIG,
        CHANNEL_COUNT,
        NDVALID_IGNORE,
        NDVALID_READ,
        DCLK_HIGH,
        DCLK_LOW,
        DCLK_CONFIG,
        DCLKWait,
        ADC_RANGE,
        BIT_RATE,
    ):
        self.regsSize = 255
        self.CONV_LOW_INT = CONV_LOW_INT
        self.CONV_HIGH_INT = CONV_HIGH_INT
        self.CONV_CONFIG = CONV_CONFIG
        self.CLC_HIGH = CLK_HIGH
        self.CLC_LOW = CLK_LOW
        self.DDC_CLK_CONFIG = DDC_CLK_CONFIG
        self.CHANNEL_COUNT = CHANNEL_COUNT
        self.NDVALID_IGNORE = NDVALID_IGNORE
        self.NDVALID_READ = NDVALID_READ
        self.DCLK_HIGH = DCLK_HIGH
        self.DCLK_LOW = DCLK_LOW
        self.DCLK_CONFIG = DCLK_CONFIG
        self.DCLK_WAIT_MCLK = DCLKWait
        self.CLK_CFG_HI = 3
        self.CLK_CFG_LO = 3
        self.CONV_WAIT_LOW = 1550
        self.CONV_WAIT_HIGH = 1550
        self.CLKDELAY_AROUND_CONV = 0

        self.DDCbit13 = 0  # CLKDIV
        self.DDCbit10 = self.adc_ranges[ADC_RANGE][0]
        self.DDCbit9 = self.adc_ranges[ADC_RANGE][1]
        self.DDCbit8 = self.bit_rates[BIT_RATE]

        self.DDCbit7 = 0  # SPEED
        self.DDCbit4 = 0  # SLEW
        self.DDCbit0 = 0  # TEST

        self.CFGLOW = (self.DDCbit7 << 7) + (self.DDCbit4 << 4) + self.DDCbit0
        self.CFGHIGH = (
            (self.DDCbit13 << 5)
            + (self.DDCbit10 << 2)
            + (self.DDCbit9 << 1)
            + self.DDCbit8
        )

        self.RegsIn = (self.int32_t * self.regsSize)()
        self.RegsOut = (self.int32_t * self.regsSize)()
        self.RegsEnable = (self.int32_t * self.regsSize)()

    def reset_regs(self):
        for i in range(self.regsSize):
            self.RegsEnable[i] = 0

    def set_reg_in(self, reg, val):
        self.RegsIn[reg] = val & 0xFF
        self.RegsEnable[reg] = 1

    def set_regs(self):
        channel_value = min(8, int(math.log2(self.CHANNEL_COUNT)))

        self.set_reg_in(0x01, (self.CONV_LOW_INT - 1) >> 16)
        self.set_reg_in(0x02, (self.CONV_LOW_INT - 1) >> 8)
        self.set_reg_in(0x03, (self.CONV_LOW_INT - 1))
        self.set_reg_in(0x04, (self.CONV_HIGH_INT - 1) >> 16)
        self.set_reg_in(0x05, (self.CONV_HIGH_INT - 1) >> 8)
        self.set_reg_in(0x06, (self.CONV_HIGH_INT - 1))

        self.set_reg_in(0x07, (self.CLC_HIGH << 4) | (self.CLC_LOW & 0x0F))
        self.set_reg_in(0x08, self.DDC_CLK_CONFIG)

        self.FORMAT = self.CFGHIGH & 1

        self.set_reg_in(0x09, (self.FORMAT << 4) | (channel_value & 0x0F))

        self.set_reg_in(0x0A, (self.DCLK_HIGH << 4) | (self.DCLK_LOW & 0x0F))
        self.set_reg_in(0x0B, self.DCLK_CONFIG)

        self.set_reg_in(0x0C, self.NDVALID_IGNORE)
        self.set_reg_in(0x0D, self.NDVALID_READ)
        self.set_reg_in(0x0E, self.NDVALID_READ >> 8)
        self.set_reg_in(0x0F, self.NDVALID_READ >> 16)

        self.set_reg_in(0x13, self.DCLK_WAIT_MCLK >> 8)
        self.set_reg_in(0x14, self.DCLK_WAIT_MCLK)

        self.set_reg_in(0x1F, self.FORMAT)

        self.set_reg_in(0x20, (self.CLK_CFG_HI << 4) | (self.CLK_CFG_LO & 0x0F))

        self.set_reg_in(0x57, self.CONV_CONFIG)

        self.set_reg_in(0x51, self.CONV_WAIT_LOW >> 8)
        self.set_reg_in(0x52, self.CONV_WAIT_LOW)
        self.set_reg_in(0x53, self.CONV_WAIT_HIGH >> 8)
        self.set_reg_in(0x54, self.CONV_WAIT_HIGH)
        self.set_reg_in(0xEB, self.CLKDELAY_AROUND_CONV)

    def get_data(self, file_path, file_index):
        filename = f"{file_path}_{file_index+1}.txt"

        hDLL = ctypes.WinDLL("USB_IO_for_VB6.dll")
        WriteFPGARegsC = self.WriteFPGARegsC_type(("WriteFPGARegsC", hDLL))
        FastAllDataCap = self.FastAllDataCap_type(("FastAllDataCap", hDLL))

        self.reset_regs()
        self.set_regs()

        USBdev = self.int16_t(0)
        DUTSelect = self.int32_t(0)

        res_write = WriteFPGARegsC(
            ctypes.byref(USBdev),
            ctypes.byref(DUTSelect),
            self.RegsIn,
            self.RegsOut,
            self.RegsEnable,
        )
        if res_write:
            return f"Can't write registers to FPGA in file {filename}"

        Channels = 256
        ArrSize = 2 * Channels
        Samples = 512
        AllDataAorBfirst = self.int32_t(0)

        AVGArr = (ctypes.c_double * ArrSize)()
        RMSArr = (ctypes.c_double * ArrSize)()
        P2PArr = (ctypes.c_double * ArrSize)()
        MAXArr = (ctypes.c_double * ArrSize)()
        MINArr = (ctypes.c_double * ArrSize)()
        AllData = (ctypes.c_double * (2 * Samples * Channels))()

        for j in range(ArrSize):
            AVGArr[j] = 0.0
            RMSArr[j] = 0.0
            P2PArr[j] = 0.0
            MAXArr[j] = 0.0
            MINArr[j] = 0.0

        for j in range(2 * Samples * Channels):
            AllData[j] = 0.0

        res_data_capture = FastAllDataCap(
            AVGArr,
            RMSArr,
            P2PArr,
            MAXArr,
            MINArr,
            ArrSize,
            Channels,
            2 * Samples,
            AllData,
            ctypes.byref(AllDataAorBfirst),
        )

        if res_data_capture:
            return f"Can't capture data from FPGA in file {filename}"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w") as dataFile:
            for type_ in ["A", "B"]:
                for c in range(Channels, 0, -1):
                    for s in range(Samples):
                        prefix = "0" if c < 10 else ""
                        shift = 0 if type_ == "A" else Channels
                        dataFile.write(
                            f"{prefix}{c}{type_}, {0}, {AllData[2*s*Channels+c-1+shift]}, {0}, {0}, {next(k for k, v in self.bit_rates.items() if v == self.DDCbit8)}\n"
                        )

        return f"File {filename} was saved successfully"

    def convert_adc(self, value):
        power = next(k for k, v in self.bit_rates.items() if v == self.DDCbit8)
        adc_range = 1e-12 * float(
            next(
                k
                for k, v in self.adc_ranges.items()
                if v == (self.DDCbit10, self.DDCbit9)
            )
        )
        return value / (2**power - 1) * adc_range
