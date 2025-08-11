#!/usr/bin/env python3
"""
Debug script to test WebSocket connection step by step.
"""

import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_websocket():
    """Debug WebSocket connection step by step."""
    server_url = "ws://localhost:8001/ws/client1"
    
    try:
        logger.info(f"🔗 Connecting to: {server_url}")
        websocket = await websockets.connect(server_url)
        logger.info("✅ Connected successfully!")
        
        # Send handshake
        handshake = {
            "type": "handshake",
            "user_id": "1", 
            "client_type": "desktop"
        }
        logger.info(f"📤 Sending handshake: {handshake}")
        await websocket.send(json.dumps(handshake))
        logger.info("✅ Handshake sent")
        
        # Listen for response
        logger.info("👂 Listening for response...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"📥 Received: {response}")
            
            # Parse response
            try:
                data = json.loads(response)
                logger.info(f"📋 Parsed response: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse JSON: {e}")
                
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for response")
            
        # Test voice command
        logger.info("🎤 Testing voice command...")
        voice_command = {
            "type": "voice_command",
            "data": {
                "query": "test message",
                "context": {}
            }
        }
        logger.info(f"📤 Sending voice command: {voice_command}")
        await websocket.send(json.dumps(voice_command))
        
        # Wait for AI response
        logger.info("👂 Waiting for AI response...")
        try:
            ai_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            logger.info(f"📥 AI Response: {ai_response[:200]}...")
            
            # Parse AI response
            try:
                ai_data = json.loads(ai_response)
                logger.info(f"📋 AI Response type: {ai_data.get('type')}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse AI response JSON: {e}")
                
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for AI response")
        
        # Clean disconnect
        logger.info("🔒 Disconnecting...")
        await websocket.close()
        logger.info("✅ Disconnected cleanly")
        
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_websocket())
