from google.cloud import vision

def detect_text(path):
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    print('Textes détectés :')
    for text in texts:
        print(f'\n"{text.description}"')

    if response.error.message:
        raise Exception(f'{response.error.message}')

if __name__ == '__main__':
    image_path = "../Use_Case_1/entretient_technique_OCR_cas_1_a.jpg"
    detect_text(image_path)