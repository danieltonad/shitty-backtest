import websockets, asyncio, json
from .memory import memory


class CapitalSocket:
    def __init__(self):
        self.websocket = None
        self.running = False
        self.subscribed_epics = set()
        self._listen_task = None

    
    async def connect_websocket(self):
        """Connect to Capital.com WebSocket if not already connected."""
        if not self.websocket:
            uri = "wss://api-streaming-capital.backend-capital.com/connect"
            self.websocket = await websockets.connect(uri, ping_interval=60, ping_timeout=30)
            self.running = True
            
            if not self._listen_task or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen())
            print("WebSocket connected.")
            
    async def ping_socket(self):
        """Ping socket service to keep connection alive."""
        try:
            ping_msg = {
                "destination": "ping",
                "correlationId": "ping_XGXXXTX",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"]
            }
            
            if self.running:
                await self.websocket.send(json.dumps(ping_msg))
            
        except Exception as e:
            print(f"Ping error: {e}")
            self.running = False
            
            
    async def subscribe_to_epic(self, epic: str):
        """Subscribe to real-time data for a given epic."""
        try:
            await self.connect_websocket()
            if epic in self.subscribed_epics:
                print(f"Already subscribed to {epic}")
                return
            
            subscribe_msg = {
                "destination": "marketData.subscribe",
                "correlationId": f"epic_sub_{epic}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                "payload": {"epics": [epic]}
            }
            await self.websocket.send(json.dumps(subscribe_msg))
            self.subscribed_epics.add(epic)
            print(f"Subscribed to {epic}")

        except Exception as e:
            print(f"Subscription error for {epic}: {e}")
            await asyncio.sleep(1 * 60)  # 1 minute sleep
            await self.subscribe_to_epic(epic)



    async def _listen(self):
        """Listen for incoming WebSocket messages and handle reconnections."""
        try:
            while self.running and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=300)
                    data = json.loads(message)

                    if data["destination"] == "marketData.subscribe":
                        print(f"Subscription confirmed: {data['payload']}")
                    elif data["destination"] == "marketData.unsubscribe":
                        print(f"Unsubscribed: {data['payload']}")
                    elif data["destination"] == "quote":
                        payload = data["payload"]
                        await memory.append_tick_data(
                            epic=payload["epic"],
                            ask=payload["ofr"],
                            bid=payload["bid"],
                            timestamp=payload["timestamp"]
                        )

                except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
                    print(f"WebSocket error or timeout: {e}")
                    break  # Exit inner loop to reconnect

        except Exception as e:
            print(f"Unhandled WebSocket error: {str(e)}")

        finally:
            self.running = False
            if self.websocket:
                try:
                    await self.websocket.close()
                except Exception as close_error:
                    print(f"Error closing WebSocket: {close_error}")
                self.websocket = None

            self._listen_task = None  # Mark task as finished
            print("WebSocket disconnected. Attempting to reconnect...")
            await asyncio.sleep(1)  # Prevent reconnect flood

            # Resubscribe to previous epics after reconnect
            epics = list(self.subscribed_epics)
            self.subscribed_epics.clear()
            for epic in epics:
                await self.subscribe_to_epic(epic)
                await asyncio.sleep(0.5)



capital_socket = CapitalSocket()