# নতুন এবং স্টেবল পাইথন ইমেজ ব্যবহার করা হচ্ছে
FROM python:3.10-slim-bullseye

# ওয়ার্কিং ডিরেক্টরি সেট করা
WORKDIR /app

# সিস্টেম ডিপেন্ডেন্সি ইনস্টল (এখানে রিপোজিটরি আপডেট হবে)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# সব ফাইল প্রোজেক্ট ফোল্ডারে কপি করা
COPY . .

# লাইব্রেরি ইনস্টল করা
RUN pip3 install --no-cache-dir -r requirements.txt

# বট রান করার কমান্ড
CMD ["python3", "main.py"]
