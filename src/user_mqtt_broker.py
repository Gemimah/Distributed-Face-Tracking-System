#!/usr/bin/env python3
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
            client_socket.send(b'\x20\x02\x00\x00')  # CONNACK with return code 0
            
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
                        client_socket.send(b'\xd0\x00')  # PINGRESP
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
            suback = b'\x90\x03' + packet_id + b'\x00'  # SUBACK with QoS 0
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
                    message = b'\x30'  # PUBLISH with QoS 0, no retain, no DUP
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
        print("\n🛑 Stopping MQTT broker...")
        broker.stop()

if __name__ == "__main__":
    main()
