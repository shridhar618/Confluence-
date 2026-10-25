import { io } from 'socket.io-client'

let ghostSocket = null

export function getGhostSocket() {
  if (!ghostSocket) {
    ghostSocket = io('/', {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })
  }

  return ghostSocket
}
