#!/usr/bin/env python3
"""Simple test script for the simplified WebSocket transcription API."""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Test the simplified WebSocket transcription API."""
    uri = "ws://localhost:8080/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")

            # Wait for connection message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {data}")

            if data.get("type") == "connected":
                print("✅ Successfully connected to transcription service!")

                # Send some dummy audio data for testing
                # In a real scenario, you'd send actual PCM audio data
                dummy_audio = b'\x00\x01\x02\x03' * 100  # 400 bytes of dummy data

                print("Sending dummy audio data...")
                await websocket.send(dummy_audio)

                # Listen for responses
                try:
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        print(f"Received: {data}")
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the API server is running with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8080")

if __name__ == "__main__":
    print("Testing simplified WebSocket transcription API...")
    asyncio.run(test_websocket())