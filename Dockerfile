FROM python:3.11-slim
WORKDIR /project/binance_trade

COPY requirements.txt ./
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD ["gunicorn", "start:app", "-c", "./gunicorn.conf.py"]