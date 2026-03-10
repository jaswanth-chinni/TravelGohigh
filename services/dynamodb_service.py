import os
import boto3
from boto3.dynamodb.conditions import Attr

REGION      = os.getenv('AWS_DEFAULT_REGION', 'ap-south-1')
USE_MOCK_DB = os.getenv('USE_MOCK_DB', 'false').lower() == 'true'

# ── In-memory store (used automatically if DynamoDB is unreachable) ──
_mem_users    = {}   # email -> user_dict
_mem_bookings = {}   # booking_id -> booking_dict
_using_memory = False

def _check_dynamo():
    """Try a cheap call to see if DynamoDB is reachable. Returns True if OK."""
    try:
        boto3.client('dynamodb', region_name=REGION).list_tables(Limit=1)
        return True
    except Exception as e:
        print(f"[DB] DynamoDB unreachable, using in-memory store: {e}")
        return False

# Decide at startup (or first use)
_dynamo_ok = None

def _dynamo_available():
    global _dynamo_ok
    if USE_MOCK_DB:
        return False
    if _dynamo_ok is None:
        _dynamo_ok = _check_dynamo()
    return _dynamo_ok

def _db():
    return boto3.resource('dynamodb', region_name=REGION)

def _users_table():
    return _db().Table('travelgo_users')

def _bookings_table():
    return _db().Table('travelgo_bookings')

# ──────────────────── USERS ────────────────────

def create_user(user_data):
    if _dynamo_available():
        _users_table().put_item(Item=user_data)
    else:
        _mem_users[user_data['email']] = user_data
        print(f"[MEM] User saved: {user_data['email']}")

def get_user(email):
    if _dynamo_available():
        resp = _users_table().get_item(Key={'email': email})
        return resp.get('Item')
    else:
        return _mem_users.get(email)

# ──────────────────── BOOKINGS ────────────────────

def create_booking(booking_data):
    # Strip out any None / null values — DynamoDB rejects them
    clean = {k: v for k, v in booking_data.items() if v is not None and v != ''}
    if _dynamo_available():
        _bookings_table().put_item(Item=clean)
    else:
        _mem_bookings[clean['booking_id']] = clean
        print(f"[MEM] Booking saved: {clean['booking_id']}")

def get_booking(booking_id):
    if _dynamo_available():
        resp = _bookings_table().get_item(Key={'booking_id': booking_id})
        return resp.get('Item')
    else:
        return _mem_bookings.get(booking_id)

def get_user_bookings(email):
    if _dynamo_available():
        resp  = _bookings_table().scan(FilterExpression=Attr('user_email').eq(email))
        items = resp.get('Items', [])
    else:
        items = [b for b in _mem_bookings.values() if b.get('user_email') == email]
    items.sort(key=lambda x: x.get('book_date', ''), reverse=True)
    return items

def cancel_booking(booking_id, email):
    if _dynamo_available():
        _bookings_table().update_item(
            Key={'booking_id': booking_id},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'cancelled'}
        )
    else:
        if booking_id in _mem_bookings:
            _mem_bookings[booking_id]['status'] = 'cancelled'
            print(f"[MEM] Booking cancelled: {booking_id}")
