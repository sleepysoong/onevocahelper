from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
import os
import uuid
import logging
from pathlib import Path

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('server.log', 'a', 'utf-8'),
        logging.StreamHandler()
    ]
)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.disabled = True

app = Flask(__name__)
app.template_folder = 'templates'

client = genai.Client(api_key=os.getenv("API_KEY"))

ALLOWED_EXTENSIONS = {'jpeg', 'jpg', 'png', 'heic'}

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

PROMPT = """
<request>
I want to organize English vocabulary words into a CSV file for studying English.
Please analyze the image and organize it into English words, phrases or mass and their Korean meanings.
but replace ',' with ' / ' [e.g., 'test, test' => 'test / test', 'test,test' => 'test / test'].
Just respond with the CSV content without any other response. This is important.
</request>
<detail>
T row: Words or English with symbols (e.g., do-did-done)
D row: Korean meaning (e.g, ~을 하다)
P row: (leave empty)
E row: (leave empty)
</detail>
<example>
No,T,D,P,E
1,do-did-done,~을 하다 / 수행하다,,
2,ring-rang-rung,전화하다 / 울리다,,
3,go-went-gone,가다 / 작동하다,,
4,give-gave-given,~을 주다,,
5,begin-began-begun,시작하다 / 시작되다,,
6,know-knew-known,~을 알고 있다,,
7,grow-grew-grown,자라다 / 키우다,,
8,throw-threw-thrown,~을 던지다 / 쏟아붓다,,
9,see-saw-seen,~을 보다,,
10,write-wrote-written,~을 쓰다,,
11,forget-forgot-forgotten,~을 잊다,,
12,take-took-taken,~을 갖다,,
13,fall-fell-fallen,떨어지다,,
14,break-broke-broken,~을 깨다 / 부서지다,,
15,eat-ate-eaten,~을 먹다,,
16,ride-rode-ridden,~을 타다 / 승마하다,,
17,forbid-forbade-forbidden,~하는 것을 금하다,,
18,run-ran-run,달리다/운영하다,,
19,become-became-become,~이 되다,,
20,make-made-made,~을 만들다,,
21,keep-kept-kept,~을 유지하다 / 계속하다,,
22,build-built-built,굳히다 / 건축하다,,
23,spend-spent-spent,~을 쓰다 / 들이다,,
24,bring-brought-brought,~을 가져오다,,
25,think-thought-thought,~을 생각하다,,
26,seek-sought-sought,~을 찾다 / 구하다,,
27,leave-left-left,떠나다 / 남겨지다,,
28,lose-lost-lost,~을 잃어버리다,,
29,send-sent-sent,~을 보내다,,
30,feel-felt-felt,느끼다,,
31,feed-fed-fed,~에게 먹이를 주다,,
32,find-found-found,~을 발견하다 / 찾다,,
33,sell-sold-sold,~을 팔다,,
34,tell-told-told,~을 말하다 / 구분하다,,
35,lead-led-led,~을 안내하다 / 이끌다,,
36,stand-stood-stood,서다 / ~이다 / 참다,,
37,hold-held-held,~을 잡다 / 유지하다,,
38,win-won-won,이기다 / 우승하다,,
39,spread-spread-spread,~을 펴다 / 퍼뜨리다,,
40,cut-cut-cut,~을 자르다 / 베다,,
41,hit-hit-hit,~을 치다 / 때리다,,
42,let-let-let,~을 하게 허락하다,,
43,access,~에 접근하다,,
44,accept,~을 받아들이다,,
45,accommodate,~에 맞추다 / 각색하다,,
46,account,설명하다 / 책임지다,,
47,accumulate,~을 축적하다 / 쌓아올리다,,
48,achieve,~을 성취하다,,
49,act,역할을 하다 / 행동하다,,
50,adapt,~을 맞추다 / 각색하다,,
51,address,~을 다루다 / 연설하다,,
52,advertise,~을 광고하다,,
53,advise,~에게 조언하다,,
54,affect,~에 영향을 주다,,
55,agree,~에 동의하다,,
56,allow,~하도록 허락하다,,
57,alter,~을 바꾸다,,
58,apologize,(to/for) 사과하다,,
59,appear,나타나다 / ~인것같다,,
60,apply,작용하다 /(for) 신청하다,,
61,argue,다투다 / (for) 주장하다,,
62,assign,~에게 맡기다 / 배정하다,,
63,assist,~을 돕다 / 거들다,,
64,associate,~을 연상시키다,,
65,assume,~라는 것으로 추정하다,,
66,assure,~을 확신시키다,,
67,attach,~을 붙여두다 / 파견하다,,
68,attack,~을 공격하다,,
69,avoid,~을 피하다 / 막다,,
70,believe,~을 믿다 / 신뢰하다,,
71,carve,~을 새기다 / 조각하다,,
72,cause,~을 야기하다 / 초래하다,,
73,challenge,~에 도전하다,,
74,charge,~에게 요금을 청구하다,,
75,communicate,(with) 의사소통하다 / 통신하다,,
76,compensate,(for) ~에 대해 보상하다,,
77,compete,경쟁하다,,
78,complain,(about/of)~에 대해 불평하다,,
79,complete,~을 완료하다 / 끝내다,,
80,compose,(on) 진정시키다,,
81,concentrate,~을 집중하다 / 몰두하다,,
...
</example>
"""


def is_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_unique_filepath(filename):
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    while True:
        file_uuid = str(uuid.uuid4())
        new_filename = f"{file_uuid}.{extension}"
        file_path = TEMP_DIR / new_filename
        
        if not file_path.exists():
            return file_path, file_uuid


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_content():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not is_allowed_file(file.filename):
            return jsonify({'error': 'Unsupported file format'}), 400
            
        try:
            file_path, file_uuid = get_unique_filepath(file.filename)
            file.save(file_path)
            logging.info(f"File saved successfully (UUID: {file_uuid}, Extension: {file_path.suffix[1:]})")
        except Exception as img_error:
            logging.error(f"Image Processing Error: {str(img_error)}")
            return jsonify({'error': f'An error occurred while processing the Image: {str(img_error)}'}), 500
        
        try:
            result = client.models.generate_content(
                model="gemini-2.5-pro-exp-03-25",
                contents=[
                    client.files.upload(file=str(file_path)),
                    "\n\n",
                    PROMPT
                ],
            ).text
            
            logging.info(f"Content Generation Successful for {file_path.name} > {result.replace("\n", " ")}")
            
            if file_path.exists():
                file_path.unlink()
                
            return jsonify({'result': result})
            
        except Exception as api_error:
            logging.error(f"Gemini Error: {str(api_error)}")

            if file_path.exists():
                file_path.unlink()

            return jsonify({'error': f'An error occurred while generating content: {str(api_error)}'}), 500
        
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=40123)
