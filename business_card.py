import qrcode
import svgwrite

# Create QR code as PNG, then embed as image in SVG
qr = qrcode.QRCode(box_size=4, border=1)
qr.add_data("https://derekbaier.com")
qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white")
png_path = "/tmp/qr.png"
qr_img.save(png_path)

# Create SVG business card 3x2 inches at 96 DPI (~288x192 px)
width, height = 288, 192
dwg = svgwrite.Drawing("/tmp/business_card.svg", size=(f"{width}px", f"{height}px"))

# Background (black anodized aluminum, but just rectangle)
dwg.add(dwg.rect(insert=(0,0), size=(width, height), fill="black"))

# Text styling (engraving represented as white)
dwg.add(dwg.text("Derek Baier", insert=(20,40), fill="white", font_size="24px", font_family="Arial"))
dwg.add(dwg.text("Email: derek.m.baier@gmail.com", insert=(20,80), fill="white", font_size="16px", font_family="Arial"))
dwg.add(dwg.text("Phone: +1 603-545-8197", insert=(20,110), fill="white", font_size="16px", font_family="Arial"))

# Embed QR code
dwg.add(dwg.image(href=png_path, insert=(width-120, height-120), size=("100px","100px")))

dwg.save()