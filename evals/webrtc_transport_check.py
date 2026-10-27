"""Real local aiortc/SmallWebRTC handshake; no model, cloud, mic or runner."""
import asyncio
import json
from pathlib import Path
from aiortc import RTCPeerConnection,RTCConfiguration,RTCSessionDescription
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

async def main():
    client=RTCPeerConnection(RTCConfiguration(iceServers=[]))
    server=SmallWebRTCConnection(ice_servers=[])
    channel=client.createDataChannel('pipecat')
    opened=asyncio.Event()
    received=asyncio.Future()
    @channel.on('open')
    def on_open():opened.set()
    @channel.on('message')
    def on_message(message):
        if not received.done():received.set_result(message)
    try:
        client.addTransceiver('audio',direction='sendrecv')
        await client.setLocalDescription(await client.createOffer())
        await server.initialize(sdp=client.localDescription.sdp,type='offer')
        answer=server.get_answer()
        await client.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'],type=answer['type']))
        await asyncio.wait_for(opened.wait(),15)
        server.send_app_message({'type':'acceptance-ping','generation_id':'synthetic-generation'})
        message=await asyncio.wait_for(received,5)
        result={'real_webrtc':True,'models_loaded':False,'cloud_used':False,'data_channel_label':channel.label,'client_connection_state':client.connectionState,'server_message':json.loads(message) if isinstance(message,str) else str(message)}
        Path('docs/webrtc-transport-results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    finally:
        await client.close()
        await server.disconnect()
asyncio.run(main())
