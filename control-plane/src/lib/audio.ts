export function decodeBase64Audio(
  base64String: string,
  mimeType = 'audio/mpeg',
  sampleRate = 44100,
  numChannels = 1
): string {
  const byteString = atob(base64String)
  const byteArray = new Uint8Array(byteString.length)

  for (let i = 0; i < byteString.length; i += 1) {
    byteArray[i] = byteString.charCodeAt(i)
  }

  let blob: Blob

  if (mimeType === 'audio/pcm16') {
    const wavHeader = createWavHeader(byteArray.length, sampleRate, numChannels)
    const wavData = new Uint8Array(wavHeader.length + byteArray.length)
    wavData.set(wavHeader, 0)
    wavData.set(byteArray, wavHeader.length)
    blob = new Blob([wavData], { type: 'audio/wav' })
  } else {
    blob = new Blob([byteArray], { type: mimeType })
  }

  return URL.createObjectURL(blob)
}

function createWavHeader(
  dataLength: number,
  sampleRate: number,
  numChannels: number
): Uint8Array {
  const header = new ArrayBuffer(44)
  const view = new DataView(header)
  const blockAlign = numChannels * 2
  const byteRate = sampleRate * blockAlign

  view.setUint32(0, 0x52494646, false)
  view.setUint32(4, 36 + dataLength, true)
  view.setUint32(8, 0x57415645, false)
  view.setUint32(12, 0x666d7420, false)
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  view.setUint32(36, 0x64617461, false)
  view.setUint32(40, dataLength, true)

  return new Uint8Array(header)
}
