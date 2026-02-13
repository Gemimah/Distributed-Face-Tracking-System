#!/usr/bin/env python3
"""
Script to copy required files to VPS
"""
import os
import subprocess
import sys

def create_mqtt_broker_on_vps():
    """Create the MQTT broker file on VPS"""
    broker_code = '''#!/usr/bin/env python3
"""
Lightweight MQTT broker that runs in user space (no sudo required)
"""
import socket
import threading
import time
import struct
import logging
from typing import Dict, Set, Callable, Any

# Set up logging
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
        """Start the MQTT broker"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"🚀 MQTT Broker started on {self.host}:{self.port}")
        logger.info("🌈 Rainbows team MQTT broker is ready!")
        
        # Start accepting connections
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
    def _accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"📡 New connection from {address}")
                
                # Start client handler thread
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
        """Handle individual client connection"""
        try:
            # Send CONNACK
            client_socket.send(b'\\x20\\x02\\x00\\x00')  # CONNACK with return code 0
            
            while self.running:
                try:
                    # Read fixed header
                    fixed_header = client_socket.recv(2)
                    if not fixed_header:
                        break
                        
                    message_type = fixed_header[0] >> 4
                    flags = fixed_header[0] & 0x0F
                    remaining_length = self._decode_remaining_length(client_socket)
                    
                    if message_type == 3:  # PUBLISH
                        self._handle_publish(client_socket, flags, remaining_length)
                    elif message_type == 8:  # SUBSCRIBE
                        self._handle_subscribe(client_socket, remaining_length)
                    elif message_type == 12:  # PINGREQ
                        client_socket.send(b'\\xd0\\x00')  # PINGRESP
                    else:
                        # Skip unknown message types
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
        """Decode MQTT remaining length field"""
        multiplier = 1
        length = 0
        encoded_byte = None
        
        while True:
            encoded_byte = client_socket.recv(1)[0]
            length += (encoded_byte & 127) * multiplier
            if encoded_byte & 128 == 0:
                break
            multiplier *= 128
            
        return length
        
    def _handle_publish(self, client_socket, flags, remaining_length):
        """Handle PUBLISH message"""
        try:
            # Read topic length and topic
            topic_length_bytes = client_socket.recv(2)
            topic_length = struct.unpack('>H', topic_length_bytes)[0]
            topic = client_socket.recv(topic_length).decode('utf-8')
            
            # Read payload (remaining bytes after topic)
            payload_length = remaining_length - 2 - topic_length
            payload = client_socket.recv(payload_length)
            
            logger.info(f"📨 Published to '{topic}': {payload[:50]}...")
            
            # Forward to subscribed clients
            self._forward_message(topic, payload)
            
        except Exception as e:
            logger.error(f"Error handling PUBLISH: {e}")
            
    def _handle_subscribe(self, client_socket, remaining_length):
        """Handle SUBSCRIBE message"""
        try:
            # Read packet identifier
            packet_id = client_socket.recv(2)
            
            # Read topic filter and QoS
            topic_length_bytes = client_socket.recv(2)
            topic_length = struct.unpack('>H', topic_length_bytes)[0]
            topic = client_socket.recv(topic_length).decode('utf-8')
            qos = client_socket.recv(1)[0]
            
            logger.info(f"📡 Client subscribed to '{topic}'")
            
            # Add to subscriptions
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(client_socket)
            
            # Send SUBACK
            suback = b'\\x90\\x03' + packet_id + b'\\x00'  # SUBACK with QoS 0
            client_socket.send(suback)
            
        except Exception as e:
            logger.error(f"Error handling SUBSCRIBE: {e}")
            
    def _forward_message(self, topic, payload):
        """Forward message to all subscribed clients"""
        if topic in self.subscriptions:
            disconnected_clients = set()
            
            for client in self.subscriptions[topic]:
                try:
                    # Create PUBLISH message
                    topic_bytes = topic.encode('utf-8')
                    message = b'\\x30'  # PUBLISH with QoS 0, no retain, no DUP
                    message += struct.pack('!H', len(topic_bytes))
                    message += topic_bytes
                    message += payload
                    
                    client.send(message)
                    
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.subscriptions[topic].discard(client)
                
    def _disconnect_client(self, client_socket):
        """Clean up disconnected client"""
        if client_socket in self.clients:
            del self.clients[client_socket]
            
        # Remove from all subscriptions
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_socket)
            
        try:
            client_socket.close()
        except:
            pass
            
    def stop(self):
        """Stop the MQTT broker"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("🛑 MQTT Broker stopped")

def main():
    """Main function to run the MQTT broker"""
    print("🌈 Rainbows Team MQTT Broker")
    print("=" * 50)
    print("Starting lightweight MQTT broker...")
    print("No sudo privileges required!")
    print("=" * 50)
    
    broker = SimpleMQTTBroker(host='0.0.0.0', port=1883)
    
    try:
        broker.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\\n🛑 Stopping MQTT broker...")
        broker.stop()

if __name__ == "__main__":
    main()
'''
    
    with open('user_mqtt_broker.py', 'w') as f:
        f.write(broker_code)
    
    print("✅ Created user_mqtt_broker.py")

def create_websocket_backend():
    """Create the websocket backend file on VPS"""
    backend_code = '''#!/usr/bin/env python3
"""
WebSocket Backend for Rainbows Team Face-Locking System
Relays MQTT messages to WebSocket clients for real-time dashboard
"""
import asyncio
import websockets
import json
import time
import paho.mqtt.client as mqtt
import threading
from typing import Set

# ===================== CONFIGURATION =====================
TEAM_ID = "rainbows"  # Your unique team identifier
MQTT_BROKER_HOST = "157.173.101.159"  # Your VPS MQTT broker
MQTT_BROKER_PORT = 1883
WEBSOCKET_PORT = 9002
MQTT_TOPIC = f"vision/{TEAM_ID}/movement"
MQTT_HEARTBEAT_TOPIC = f"vision/{TEAM_ID}/heartbeat"

# ===================== GLOBAL VARIABLES =====================
websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
mqtt_client = None
latest_movement_data = None
latest_heartbeat_data = {}

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        # Subscribe to topics
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
        
        # Broadcast to all WebSocket clients
        asyncio.create_task(broadcast_to_websockets({
            'type': 'mqtt_message',
            'topic': msg.topic,
            'payload': payload
        }))
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

async def handle_websocket(websocket, path):
    """Handle WebSocket connections"""
    global websocket_clients
    websocket_clients.add(websocket)
    print(f"🌐 New WebSocket client connected from {websocket.remote_address}")
    
    try:
        # Send current data to new client
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
        
        # Keep connection alive and handle messages
        async for message in websocket:
            try:
                data = json.loads(message)
                # Handle any WebSocket messages if needed
                print(f"📨 WebSocket message: {data}")
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        print(f"🌐 WebSocket client disconnected")
    finally:
        websocket_clients.discard(websocket)

async def broadcast_to_websockets(message):
    """Broadcast message to all connected WebSocket clients"""
    if websocket_clients:
        disconnected = set()
        for client in websocket_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            websocket_clients.discard(client)

def start_mqtt_client():
    """Start MQTT client in a separate thread"""
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
    """Main WebSocket server function"""
    print(f"🌈 Rainbows Team WebSocket Backend")
    print(f"📡 MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f"🌐 WebSocket Server: ws://0.0.0.0:{WEBSOCKET_PORT}")
    print("=" * 50)
    
    # Start MQTT client
    start_mqtt_client()
    
    # Start WebSocket server
    async with websockets.serve(handle_websocket, "0.0.0.0", WEBSOCKET_PORT):
        print(f"🚀 WebSocket server started on port {WEBSOCKET_PORT}")
        print("🌐 Ready to serve dashboard connections!")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 Shutting down WebSocket backend...")
'''
    
    with open('websocket_backend.py', 'w') as f:
        f.write(backend_code)
    
    print("✅ Created websocket_backend.py")

if __name__ == "__main__":
    print("🌈 Setting up Rainbows Team VPS...")
    print("=" * 40)
    
    create_mqtt_broker_on_vps()
    create_websocket_backend()
    
    print("\\n✅ Setup complete!")
    print("Now run:")
    print("1. python3 user_mqtt_broker.py")
    print("2. python3 websocket_backend.py")
    print("3. Open dashboard.html in your browser")
'''
    
    with open('setup_vps.py', 'w') as f:
        f.write(setup_code)
    
    print("✅ Created setup_vps.py")
