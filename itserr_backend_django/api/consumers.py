import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MyModelConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("WebSocket connect: ", self.channel_name)  # Aggiungi un print per il debug

        self.room_group_name = 'models'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print("WebSocket accepted")  # Verifica che la connessione sia accettata

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected: {close_code}")  # Verifica quando il WebSocket si disconnette
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print("Message received: ", text_data)  # Stampa il messaggio ricevuto dal WebSocket

        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Invia il messaggio al gruppo WebSocket
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        print(f"Sending message to WebSocket: {event['message']}")  # Stampa il messaggio inviato al WebSocket
        message = event['message']

        # Invia il messaggio al WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
