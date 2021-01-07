import qrcode
import argparse

if __name__ == "__main__":
    """
    This function is designed to create new landing targets for the drone.
    Argument order is outer code, middle code, inner code, output file path (name).
    The output file name is optional. Default name is nestedQR.png.
    This outputs a 4096x4096 pixel png image with three QR codes in it, stacked
    on top of one-another, and obscuring the middle portion of the code on the
    layer below. This results in a somewhat non-standard qr code format, and it
    relies upon error-correction built into the QR code format to work. However,
    we have tested this extensively and have found that it works well enough for
    our purposes. We have tweaked the scaling factor and quiet outer region to
    obtain close to optimal performance.
    """
    parser = argparse.ArgumentParser(description='Create 3 nested QR codes')
    # parser.add_argument('-s', '--scale', type=int, help="The relative decrease in size of each qr code. Default=3")
    parser.add_argument('outer', help="The text to be encoded into the outer QR code")
    parser.add_argument('middle', help="The text to be encoded into the middle QR code")
    parser.add_argument('inner', help="The text to be encoded into the inner QR code")
    parser.add_argument(
        '-p', '--path', help="File path for the QR code to be saved at. Should use the .png extension. Default=nestedQR.png")

    args = parser.parse_args()

    # decrease in size for each inner code
    scale = 1 / 3.2

    path = "nestedQR.png"
    if args.path:
        path = args.path
    
    # error correction of high allows aprox. 30% error
    # create outer QR code at 4096 x 4096 pixels
    outerQR = qrcode.QRCode(
        version=2,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    outerQR.add_data(args.outer)
    outerImage = outerQR.make_image()
    outerImage = outerImage.resize((4096, 4096))

    # create middle QR code at size outerImage.size() * scale
    middleQR = qrcode.QRCode(
        version=2,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    middleQR.add_data(args.middle)
    middleImage = middleQR.make_image()
    middleImage = middleImage.resize((int(outerImage.size[0] * scale), int(outerImage.size[1] * scale)))

    # create inner QR code at size middleImage.size() * scale
    innerQR = qrcode.QRCode(
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M
        )
    innerQR.add_data(args.inner)
    innerImage = innerQR.make_image()
    innerImage = innerImage.resize((int(middleImage.size[0] * scale), int(middleImage.size[1] * scale)))

    # Place middle and inner image at center of outer image
    outerImage.paste(middleImage, (int(outerImage.size[0] / 2) - int(middleImage.size[0] / 2),int(outerImage.size[1] / 2) - int(middleImage.size[1] / 2)))
    outerImage.paste(innerImage, (int(outerImage.size[0] / 2) - int(innerImage.size[0] / 2),int(outerImage.size[1] / 2) - int(innerImage.size[1] / 2)))

    outerImage.save(path)


    