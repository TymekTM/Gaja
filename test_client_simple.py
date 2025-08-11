#!/usr/bin/env python3
"""Simple test for the GAJA client connectivity."""

import asyncio
import websockets
import json

async def test_connection():
    """Test basic WebSocket connection to server."""
    try:
        uri = "ws://localhost:8001/ws/client1"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for handshake
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"Received handshake: {data}")
                
                # Send a test voice command
                test_message = {
                    "type": "voice_command",
                    "data": {
                        "query": "test message",
                        "context": {}
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                print("✅ Sent test voice command")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                print(f"Received response: {data}")
                
            except asyncio.TimeoutError:
                print("⚠️ Timeout waiting for response")
            except Exception as e:
                print(f"⚠️ Error during communication: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
