# TravelGo – AWS Deployment Guide

## Architecture
- EC2 (Ubuntu) → Flask App
- DynamoDB → Users & Bookings
- SNS → Email Notifications
- IAM → Access Roles

---

## STEP 1: Create IAM Role for EC2

1. AWS Console → IAM → Roles → Create Role
2. Trusted Entity: EC2
3. Attach policies:
   - AmazonDynamoDBFullAccess
   - AmazonSNSFullAccess
4. Name: `TravelGoEC2Role`

---

## STEP 2: Create DynamoDB Tables

Go to AWS Console → DynamoDB → Create Table

### Table 1: travelgo_users
- Partition key: `email` (String)
- Billing: On-demand

### Table 2: travelgo_bookings
- Partition key: `booking_id` (String)
- Billing: On-demand

---

## STEP 3: Create SNS Topic

1. AWS Console → SNS → Topics → Create topic
2. Type: Standard
3. Name: `TravelGoNotifications`
4. Copy the ARN → set as environment variable: `SNS_TOPIC_ARN`

### Add Email Subscription:
- Protocol: Email
- Endpoint: your-email@example.com
- Confirm the subscription email

---

## STEP 4: Launch EC2 Instance

1. AWS Console → EC2 → Launch Instance
2. AMI: Ubuntu Server 22.04 LTS
3. Instance type: t2.micro (free tier)
4. **Attach IAM Role**: TravelGoEC2Role
5. Security Group: Allow port 80 (HTTP) and 22 (SSH) from 0.0.0.0/0
6. Key pair: Create or select existing

---

## STEP 5: Setup Application on EC2

SSH into the instance:
```bash
ssh -i your-key.pem ubuntu@<EC2-Public-IP>
```

Install dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

Upload/clone your project:
```bash
# Option 1: SCP
scp -i your-key.pem -r ./travelgo ubuntu@<EC2-IP>:~/

# Option 2: Git
git clone <your-repo-url>
cd travelgo
```

Setup Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set environment variables:
```bash
export AWS_DEFAULT_REGION=ap-south-1
export SNS_TOPIC_ARN=arn:aws:sns:ap-south-1:XXXX:TravelGoNotifications
export SECRET_KEY=your-secure-random-key
```

Run the app:
```bash
sudo python3 app.py
# Or with gunicorn:
pip install gunicorn
sudo venv/bin/gunicorn -w 4 -b 0.0.0.0:80 app:app
```

Access: http://<EC2-Public-IP>

---

## STEP 6: (Optional) Auto-start with systemd

```bash
sudo nano /etc/systemd/system/travelgo.service
```

```ini
[Unit]
Description=TravelGo Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/travelgo
Environment="AWS_DEFAULT_REGION=ap-south-1"
Environment="SNS_TOPIC_ARN=arn:aws:sns:ap-south-1:XXXX:TravelGoNotifications"
Environment="SECRET_KEY=your-secure-random-key"
ExecStart=/home/ubuntu/travelgo/venv/bin/gunicorn -w 4 -b 0.0.0.0:80 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable travelgo
sudo systemctl start travelgo
```

---

## DynamoDB Table Structure Reference

### travelgo_users
| Field | Type | Description |
|-------|------|-------------|
| email | String (PK) | User email (login ID) |
| user_id | String | UUID |
| name | String | Full name |
| mobile | String | Phone number |
| password | String | Password |
| created_at | String | ISO timestamp |

### travelgo_bookings
| Field | Type | Description |
|-------|------|-------------|
| booking_id | String (PK) | TRV + UUID |
| user_id | String | User reference |
| user_email | String | For filtering |
| mode | String | flight/train/bus/hotel |
| type_id | String | Transport item ID |
| hotel_id | String | Hotel item ID |
| details | String | Human-readable summary |
| travel_date | String | Date of travel |
| passengers | Number | Passenger count |
| total_cost | String | Total ₹ amount |
| status | String | confirmed / cancelled |
| book_date | String | ISO timestamp |
