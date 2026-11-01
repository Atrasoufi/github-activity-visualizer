# استفاده از ایمیج رسمی پایتون
FROM python:3.14-slim

# جلوگیری از نوشتن فایل‌های pyc و بافر کردن لاگ‌ها
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# نصب پیش‌نیازهای سیستم‌عامل برای کامپایل و ارتباط با دیتابیس
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نصب پکیج‌های پایتون
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی کردن کدهای پروژه
COPY . /app/

# اجرای سرور توسعه روی پورت 8000
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]