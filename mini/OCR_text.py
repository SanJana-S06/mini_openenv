from PIL import Image,ImageOps
# import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

image_path = r'C:\Users\Sanjana.S\OneDrive\Desktop\project mini\mini_v1\sample_img1.png'

image = Image.open(image_path)

gray_image = ImageOps.grayscale(image)

extracted_text = pytesseract.image_to_string(gray_image)
extracted_text_list=extracted_text.split()

# Print the recognized text
print("--- Extracted Text ---")
print(extracted_text_list)
# if "whatsapp" in extracted_text:
# 	print("found shreyas")
# else:
# 	print("not found...error")
print("----------------------")