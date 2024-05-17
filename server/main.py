from typing import List, Dict  
from starlette.websockets import WebSocketDisconnect
from fastapi import FastAPI, WebSocket, status
import json


app = FastAPI()

def tabla_base():    
    return [[" "," "," "],[" "," "," "],[" "," "," "]]

table = tabla_base()
def revisar_ganador():    
    global table
    for fila in range(3):
        if table[fila][0] == table[fila][1] == table[fila][2] != " ":
            ganador = table[fila][0]
            table = tabla_base()
            return True, ganador
    for col in range(3):
        if table[0][col] == table[1][col] == table[2][col] != " ":
            ganador = table[0][col]
            table = tabla_base()
            return True, ganador
    if table[0][0] == table[1][1] == table[2][2] != " ":
        ganador = table[0][0]
        table = tabla_base()
        return True, ganador
    if table[0][2] == table[1][1] == table[2][0] != " ":
        ganador = table[1][1]
        table = tabla_base()
        return True, ganador
    return False, None

async def actualizar_tabla(manager, data):
    fila = int(data['cell'][0])
    col = int(data['cell'][1])
    data['init'] = False
    if table[fila][col] == " ":        
        table[fila][col] = data['player']
        ganaste, winner = revisar_ganador()
        if ganaste:
            data['message'] = "ganaste"
        elif all(cell != " " for fila in table for cell in fila):
            data['message'] = "empate"
        else:
            data['message'] = "seleccionar"
    else:
        data['message'] = "Escoge otra celda"
    await manager.broadcast(data)
    if data['message'] in ['empate', 'ganaste']:
        manager.connections = []
        
class SalasDeJuego:
    def __init__(self):
        self.connections: List[WebSocket] = []
        self.table = tabla_base()

class GestorConexion:
    def __init__(self):
        self.salasJuego: List[SalasDeJuego] = []
        self.connections: List[WebSocket] = []
        self.active_players: Dict[WebSocket, str] = {}
        self.jugadores_conectados = 0

    async def connect(self, websocket: WebSocket):
        
        if len(self.connections) >= 2:
            
            await websocket.accept()
            await websocket.close(4000)
        else:
            await websocket.accept()            
            self.connections.append(websocket)
            if len(self.connections) == 1:                
                await websocket.send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Esperando a otro jugador',
                })
            else:                
                await websocket.send_json({
                    'init': True,
                    'player': 'O',
                    'message': '',
                })                
                await self.connections[0].send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Es tu turno!',
                })        
        player = 'X' if len(self.connections) == 1 else 'O'
        self.active_players[websocket] = player
        self.jugadores_conectados += 1

    async def disconnect(self, websocket: WebSocket):
        self.jugadores_conectados -= 1
        global table
        if websocket in self.connections:
            self.connections.remove(websocket)
        player = self.active_players[websocket]  
        del self.active_players[websocket]  
        for connection in self.connections:
            await connection.send_json({
                'message': 'ganaste',
                'player': 'X' if player == 'O' else 'O',  
                'info': f"El jugador {player} abandono la partida"
            })            
            await connection.close()  
        table = tabla_base() 
    async def broadcast(self, data: str):        
        for connection in self.connections:
            await connection.send_json(data)
            
manager = GestorConexion()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            await actualizar_tabla(manager, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"Errror: {e}")