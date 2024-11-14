import asyncio
import requests
from telethon import TelegramClient, events
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os

# Configuración del cliente de Telegram
API_ID = '20451779'
API_HASH = 'da79d8408831a094d64edb184f253bab'
PHONE_NUMBER = '+51903356436'

# Inicializar cliente de Telegram
client = TelegramClient('mi_sesion_token', API_ID, API_HASH)

# Usuario administrador
ADMIN_USER = 'Asteriscom'

# Archivo JSON para almacenar permisos
ARCHIVO_PERMISOS = 'memoria_permisos.json'

# Diccionario para almacenar permisos con fecha de expiración
permisos = {}

# Diccionario para registrar intentos de usuarios no autorizados
intentos_no_autorizados = {}

# Máximo de intentos antes de bloquear temporalmente
MAX_INTENTOS = 5
BLOQUEO_TIEMPO = timedelta(hours=2)

# Lista de URLs asociadas a cada comando
URLS = {
    '/denuncia': 'http://161.132.49.242:1241/token/private/31742607',
    '/consulta': 'http://161.132.49.242:1241/token/private/31900419'
}

# Registro de valores enviados previamente
valores_enviados = set()

# Cargar permisos desde el archivo JSON
def cargar_permisos():
    if os.path.exists(ARCHIVO_PERMISOS):
        with open(ARCHIVO_PERMISOS, 'r') as archivo:
            datos = json.load(archivo)
            for usuario, tiempo in datos.items():
                permisos[usuario] = datetime.fromisoformat(tiempo)

# Guardar permisos en el archivo JSON
def guardar_permisos():
    datos = {usuario: tiempo.isoformat() for usuario, tiempo in permisos.items()}
    with open(ARCHIVO_PERMISOS, 'w') as archivo:
        json.dump(datos, archivo)

# Función para obtener datos de las URLs
async def obtener_datos(url):
    """Extrae el usuario, contraseña y token del HTML de la URL proporcionada."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            usuario = soup.find(text="Usuario:").find_next('input')['value']
            password = soup.find(text="Contraseña:").find_next('input')['value']
            token = soup.find(text="Token:").find_next('input')['value']

            return usuario, password, token
        else:
            return None, None, None
    except Exception as e:
        print(f"Error al obtener los datos de la URL {url}: {str(e)}")
        return None, None, None

async def manejar_comando(event, url):
    """Maneja la respuesta para cualquier comando registrado en la lista URLS."""
    sender = await event.get_sender()
    username = sender.username

    # Verificar si el usuario tiene permisos y si no ha expirado
    if username in permisos:
        if permisos[username] > datetime.now():
            usuario, password, token = await obtener_datos(url)

            if usuario and password and token:
                chat_id = event.chat_id
                
                # Enviar cada dato individualmente
                await client.send_message(chat_id, usuario)
                await client.send_message(chat_id, password)
                await client.send_message(chat_id, token)
                
            else:
                await client.send_message(event.chat_id, "❌ Error al obtener los datos del token.")
        else:
            await client.send_message(event.chat_id, "❌ Tu membresía ha caducado contactate con @Asteriscom.")
    else:
        await client.send_message(event.chat_id, "❌ No estás autorizado para usar este comando.")

# Comandos para otorgar permisos temporales
@client.on(events.NewMessage(pattern='/vip(\d) (.+)'))
async def otorgar_permisos(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        dias = int(event.pattern_match.group(1))
        nuevo_usuario = event.pattern_match.group(2).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
        permisos[nuevo_usuario] = datetime.now() + timedelta(days=dias)
        
        # Guardar los permisos actualizados en JSON
        guardar_permisos()
        
        # Enviar confirmación al administrador y al usuario específico
        await client.send_message(event.chat_id, f"🎉 ¡Felicidades @{nuevo_usuario}, ahora cuentas con privilegios para poder consultar por {dias} días!")
        await client.send_message(nuevo_usuario, f"🎉 ¡Hola @{nuevo_usuario}, has recibido membresía VIP para consultar durante {dias} días!")
    else:
        await client.send_message(event.chat_id, "❌ No tienes permiso para otorgar privilegios.")

# Comandos para quitar permisos temporales
@client.on(events.NewMessage(pattern='/uvip(\d) (.+)'))
async def quitar_permisos(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    sender = await event.get_sender()
    username = sender.username
    
    if username == ADMIN_USER:
        dias = int(event.pattern_match.group(1))
        usuario_a_quitar = event.pattern_match.group(2).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
        
        if usuario_a_quitar in permisos:
            permisos[usuario_a_quitar] -= timedelta(days=dias)
            
            # Guardar los permisos actualizados en JSON
            guardar_permisos()
            
            # Enviar confirmación al administrador y notificación al usuario específico
            await client.send_message(event.chat_id, f"🕒 Se han restado {dias} días de la membresía de {usuario_a_quitar}.")
            await client.send_message(usuario_a_quitar, f"🕒 Tu membresía ha sido reducida en {dias} días. Contacta con {ADMIN_USER} si tienes dudas.")
        else:
            await client.send_message(event.chat_id, f"❌ No se encontraron permisos para {usuario_a_quitar}.")
    else:
        await client.send_message(event.chat_id, "❌ No tienes permiso para modificar privilegios.")

# Comando para verificar tiempo restante de membresía
@client.on(events.NewMessage(pattern='/me (.+)'))
async def verificar_membresia(event):
    # Verificar si el mensaje es privado
    if not event.is_private:
        return
    
    usuario_a_verificar = event.pattern_match.group(1).lstrip('@')  # Eliminar '@' del nombre de usuario si está presente
    
    if usuario_a_verificar in permisos:
        tiempo_restante = permisos[usuario_a_verificar] - datetime.now()
        dias, segundos = tiempo_restante.days, tiempo_restante.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        await client.send_message(event.chat_id, f"@{usuario_a_verificar} cuenta con {dias} días, {horas} horas y {minutos} minutos de membresía.")
    else:
        await client.send_message(event.chat_id, f"❌ No se encontraron permisos para {usuario_a_verificar}.")

# Registrar los comandos dinámicamente solo para usuarios con permisos
for comando, url in URLS.items():
    @client.on(events.NewMessage(pattern=comando))
    async def evento_handler(event, url=url):
        # Verificar si el mensaje es privado
        if event.is_private:
            await manejar_comando(event, url)

# Cargar permisos al iniciar el bot
cargar_permisos()

# Conexión persistente con reconexión automática en caso de error o caída de Internet
async def main():
    while True:
        try:
            await client.start(PHONE_NUMBER)
            print("Bot de token conectado y funcionando.")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Error detectado: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)  # Esperar unos segundos antes de intentar reconectar

# Iniciar el cliente de Telegram
with client:
    client.loop.run_until_complete(main())
