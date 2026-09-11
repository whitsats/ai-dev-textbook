import random
import string
from io import BytesIO

from PIL import Image, ImageFont, ImageDraw


class ImageCode:
    def get_text(self) -> str:
        chars = random.sample(string.ascii_letters + string.digits, 4)
        return "".join(chars)

    def rand_color(self):
        return (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

    def draw_lines(self, draw, num: int, width: int, height: int):
        for _ in range(num):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(height, height)
            draw.line(((x1, y1), (x2, y2)), fill="black", width=2)

    def draw_verify_code(self):
        code = self.get_text()
        width, height = 80, 38
        im = Image.new("RGB", (width, height), "white")
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/Arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(im)
        for i in range(4):
            draw.text(
                (random.randint(3, 10) + 15 * i, random.randint(3, 10)),
                text=code[i],
                fill=self.rand_color(),
                font=font,
            )
        self.draw_lines(draw, 2, width, height)
        return im, code

    def get_code(self):
        image, code = self.draw_verify_code()
        buf = BytesIO()
        image.save(buf, "jpeg")
        image_bytes = buf.getvalue()
        return code, image_bytes
