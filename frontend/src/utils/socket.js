import { io } from 'socket.io-client'

let socket = null

export function getSocket(token) {
  if (!socket) {
    socket = io('/', {
      query: { token },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })
  }
  return socket
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}
