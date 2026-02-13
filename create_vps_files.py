#!/usr/bin/env python3
"""
Create the required files for VPS setup
"""

# MQTT Broker Code
mqtt_broker_code = '''#!/usr/bin/env python3
"""
Lightweight MQTT broker that runs in user space (no sudo required)
"""
import socket
import threading
import time
import struct
import logging
from typing import Dict, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleMQTTBroker:
    def __init__(self, host='0.0.0.0', port=1883):
        self.host = host
        self.port = port
        self.clients: Dict[socket.socket, Dict] = {}
        self.subscriptions: Dict[str, Set[socket.socket]] = {}
        self.running = False
        self.server_socket = None
        
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"🚀 MQTT Broker started on {self.host}:{self.port}")
        logger.info("🌈 Rainbows team MQTT broker is ready!")
        
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
    def _accept_connections(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"📡 New connection from {address}")
                
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
                    
    def _handle_client(self, client_socket, address):
        try:
            client_socket.send(b'\\x20\\x02\\x00\\x00')
            
            while self.running:
                try:
                    fixed_header = client_socket.recv(2)
                    if not fixed_header:
                        break
                        
                    message_type = fixed_header[0] >> 4
                    remaining_length = self._decode_remaining_length(client_socket)
                    
                    if message_type == 3:  # PUBLISH
                        self._handle_publish(client_socket, remaining_length)
                    elif message_type == 8:  # SUBSCRIBE
                        self._handle_subscribe(client_socket, remaining_length)
                    elif message_type == 12:  # PINGREQ
                        client_socket.send(b'\\xd0\\x00')
                    else:
                        client_socket.recv(remaining_length)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling client {address}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Client handler error for {address}: {e}")
        finally:
            self._disconnect_client(client_socket)
            
    def _decode_remaining_length(self, client_socket):
        multiplier = 1
        length = 0
        
        while True:
            encoded_byte = client_socket.recv(1)[0]
            length += (encoded_byte & 127) * multiplier
            if encoded_byte & 128 == 0:
                break
            multiplier *= 128
            
        return length
        
    def _handle_publish(self, client_socket, remaining_length):
        try:
            topic_length_bytes = client_socket.recv(2)
            topic_length = struct.unpack('>H', topic_length_bytes)[0]
            topic = client_socket.recv(topic_length).decode('utf-8')
            
            payload_length = remaining_length - 2 - topic_length
            payload = client_socket.recv(payload_length)
            
            logger.info(f"📨 Published to '{topic}': {payload[:50]}...")
            self._forward_message(topic, payload)
            
        except Exception as e:
            logger.error(f"Error handling PUBLISH: {e}")
            
    def _handle_subscribe(self, client_socket, remaining_length):
        try:
            packet_id = client_socket.recv(2)
            
            topic_length_bytes = client_socket.recv(2)
            topic_length = struct.unpack('>H', topic_length_bytes)[0]
            topic = client_socket.recv(topic_length).decode('utf-8')
            qos = client_socket.recv(1)[0]
            
            logger.info(f"📡 Client subscribed to '{topic}'")
            
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(client_socket)
            
            suback = b'\\x90\\x03' + packet_id + b'\\x00'
            client_socket.send(suback)
            
        except Exception as e:
            logger.error(f"Error handling SUBSCRIBE: {e}")
            
    def _forward_message(self, topic, payload):
        if topic in self.subscriptions:
            disconnected_clients = set()
            
            for client in self.subscriptions[topic]:
                try:
                    topic_bytes = topic.encode('utf-8')
                    message = b'\\x30'
                    message += struct.pack('!H', len(topic_bytes))
                    message += topic_bytes
                    message += payload
                    
                    client.send(message)
                    
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")
                    disconnected_clients.add(client)
            
            for client in disconnected_clients:
                self.subscriptions[topic].discard(client)
                
    def _disconnect_client(self, client_socket):
        if client_socket in self.clients:
            del self.clients[client_socket]
            
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_socket)
            
        try:
            client_socket.close()
        except:
            pass
            
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("🛑 MQTT Broker stopped")

def main():
    print("🌈 Rainbows Team MQTT Broker")
    print("=" * 50)
    print("Starting lightweight MQTT broker...")
    print("No sudo privileges required!")
    print("=" * 50)
    
    broker = SimpleMQTTBroker(host='0.0.0.0', port=1883)
    
    try:
        broker.start()
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\\n🛑 Stopping MQTT broker...")
        broker.stop()

if __name__ == "__main__":
    main()
'''

# WebSocket Backend Code
websocket_backend_code = '''#!/usr/bin/env python3
"""
WebSocket Backend for Rainbows Team Face-Locking System
"""
import asyncio
import websockets
import json
import paho.mqtt.client as mqtt
import threading
from typing import Set

TEAM_ID = "rainbows"
MQTT_BROKER_HOST = "157.173.101.159"
MQTT_BROKER_PORT = 1883
WEBSOCKET_PORT = 9002
MQTT_TOPIC = f"vision/{TEAM_ID}/movement"
MQTT_HEARTBEAT_TOPIC = f"vision/{TEAM_ID}/heartbeat"

websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
mqtt_client = None
latest_movement_data = None
latest_heartbeat_data = {}

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        client.subscribe(MQTT_TOPIC)
        client.subscribe(MQTT_HEARTBEAT_TOPIC)
        print(f"✓ Subscribed to {MQTT_TOPIC}")
        print(f"✓ Subscribed to {MQTT_HEARTBEAT_TOPIC}")
    else:
        print(f"✗ Failed to connect to MQTT broker, return code {rc}")

def on_mqtt_message(client, userdata, msg):
    global latest_movement_data, latest_heartbeat_data
    
    try:
        payload = json.loads(msg.payload.decode())
        
        if msg.topic == MQTT_TOPIC:
            latest_movement_data = payload
            print(f"📨 MQTT Movement: {payload.get('status', 'Unknown')} | Angle: {payload.get('servo_angle', 'N/A')}°")
        elif msg.topic == MQTT_HEARTBEAT_TOPIC:
            latest_heartbeat_data[payload.get('node', 'unknown')] = payload
            print(f"💓 MQTT Heartbeat: {payload.get('node', 'unknown')} - {payload.get('status', 'Unknown')}")
        
        asyncio.create_task(broadcast_to_websockets({
            'type': 'mqtt_message',
            'topic': msg.topic,
            'payload': payload
        }))
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

async def handle_websocket(websocket, path):
    global websocket_clients
    websocket_clients.add(websocket)
    print(f"🌐 New WebSocket client connected from {websocket.remote_address}")
    
    try:
        if latest_movement_data:
            await websocket.send(json.dumps({
                'type': 'mqtt_message',
                'topic': MQTT_TOPIC,
                'payload': latest_movement_data
            }))
        
        if latest_heartbeat_data:
            await websocket.send(json.dumps({
                'type': 'heartbeat_update',
                'data': latest_heartbeat_data
            }))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"📨 WebSocket message: {data}")
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        print(f"🌐 WebSocket client disconnected")
    finally:
        websocket_clients.discard(websocket)

async def broadcast_to_websockets(message):
    if websocket_clients:
        disconnected = set()
        for client in websocket_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        for client in disconnected:
            websocket_clients.discard(client)

def start_mqtt_client():
    global mqtt_client
    
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
        print("🚀 MQTT client started")
    except Exception as e:
        print(f"❌ Failed to start MQTT client: {e}")

async def main():
    print(f"🌈 Rainbows Team WebSocket Backend")
    print(f"📡 MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f"🌐 WebSocket Server: ws://0.0.0.0:{WEBSOCKET_PORT}")
    print("=" * 50)
    
    start_mqtt_client()
    
    async with websockets.serve(handle_websocket, "0.0.0.0", WEBSOCKET_PORT):
        print(f"🚀 WebSocket server started on port {WEBSOCKET_PORT}")
        print("🌐 Ready to serve dashboard connections!")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 Shutting down WebSocket backend...")
'''

def create_files():
    """Create the required files"""
    
    with open('user_mqtt_broker.py', 'w') as f:
        f.write(mqtt_broker_code)
    
    with open('websocket_backend.py', 'w') as f:
        f.write(websocket_backend_code)
    
    print("✅ Created user_mqtt_broker.py")
    print("✅ Created websocket_backend.py")
    print("\\nNow run:")
    print("1. python3 user_mqtt_broker.py")
    print("2. python3 websocket_backend.py")

if __name__ == "__main__":
    create_files()
