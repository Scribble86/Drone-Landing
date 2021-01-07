from typing import List

from pyzbar79.pyzbar import pyzbar
from pyzbar79.pyzbar.pyzbar import Decoded
from pyzbar79.pyzbar.wrapper import ZBarSymbol


class Recognizer:
    """The Recognizer class finds images in a QR code and reports on their positions and encoded data.
    It operates by simply calling pyzbar and returning the corner point positions and the code contents."""
    @staticmethod
    def recognize(image) -> List[Decoded]:
        return pyzbar.decode(image, [ZBarSymbol.QRCODE])
