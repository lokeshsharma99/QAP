import { RunResponseContent } from '@/types/os'
import { useCallback } from 'react'

function processChunk(
  chunk: RunResponseContent,
  onChunk: (chunk: RunResponseContent) => void
) {
  onChunk(chunk)
}

// TODO: Make new format the default and phase out legacy format

function isLegacyFormat(data: RunResponseContent): boolean {
  return (
    typeof data === 'object' &&
    data !== null &&
    'event' in data &&
    !('data' in data) &&
    typeof data.event === 'string'
  )
}

interface NewFormatData {
  event: string
  data: string | Record<string, unknown>
}

type LegacyEventFormat = RunResponseContent & { event: string }

function convertNewFormatToLegacy(newFormatData: NewFormatData): LegacyEventFormat {
  const { event, data } = newFormatData

  let parsedData: Record<string, unknown>
  if (typeof data === 'string') {
    try {
      parsedData = JSON.parse(data)
    } catch {
      parsedData = {}
    }
  } else {
    parsedData = data
  }

  const { ...cleanData } = parsedData

  return {
    event: event,
    ...cleanData
  } as LegacyEventFormat
}

/**
 * Extracts complete JSON objects from a buffer string incrementally.
 * Allows partial JSON objects to accumulate across chunks.
 */
function parseBuffer(
  buffer: string,
  onChunk: (chunk: RunResponseContent) => void
): string {
  let currentIndex = 0
  let jsonStartIndex = buffer.indexOf('{', currentIndex)

  while (jsonStartIndex !== -1 && jsonStartIndex < buffer.length) {
    let braceCount = 0
    let inString = false
    let escapeNext = false
    let jsonEndIndex = -1
    let i = jsonStartIndex

    for (; i < buffer.length; i++) {
      const char = buffer[i]

      if (inString) {
        if (escapeNext) {
          escapeNext = false
        } else if (char === '\\') {
          escapeNext = true
        } else if (char === '"') {
          inString = false
        }
      } else {
        if (char === '"') {
          inString = true
        } else if (char === '{') {
          braceCount++
        } else if (char === '}') {
          braceCount--
          if (braceCount === 0) {
            jsonEndIndex = i
            break
          }
        }
      }
    }

    if (jsonEndIndex !== -1) {
      const jsonString = buffer.slice(jsonStartIndex, jsonEndIndex + 1)

      try {
        const parsed = JSON.parse(jsonString)

        if (isLegacyFormat(parsed)) {
          processChunk(parsed, onChunk)
        } else {
          const legacyChunk = convertNewFormatToLegacy(parsed as NewFormatData)
          processChunk(legacyChunk as RunResponseContent, onChunk)
        }
      } catch {
        jsonStartIndex = buffer.indexOf('{', jsonStartIndex + 1)
        continue
      }

      currentIndex = jsonEndIndex + 1
      buffer = buffer.slice(currentIndex).trim()
      currentIndex = 0
      jsonStartIndex = buffer.indexOf('{', currentIndex)
    } else {
      break
    }
  }

  return buffer
}

/**
 * Custom React hook to handle streaming API responses as JSON objects.
 *
 * Supports two streaming formats:
 * 1. Legacy format: Direct JSON objects matching RunResponseContent interface
 * 2. New format: Event/data structure with { event: string, data: string|object }
 */
export default function useAIResponseStream() {
  const streamResponse = useCallback(
    async (options: {
      apiUrl: string
      headers?: Record<string, string>
      requestBody: FormData | Record<string, unknown>
      onChunk: (chunk: RunResponseContent) => void
      onError: (error: Error) => void
      onComplete: () => void
    }): Promise<void> => {
      const { apiUrl, headers = {}, requestBody, onChunk, onError, onComplete } = options

      let buffer = ''

      try {
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            // Only set Content-Type for non-FormData requests
            ...(!(requestBody instanceof FormData) && {
              'Content-Type': 'application/json'
            }),
            ...headers
          },
          body:
            requestBody instanceof FormData
              ? requestBody
              : JSON.stringify(requestBody)
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw errorData
        }

        if (!response.body) {
          throw new Error('No response body')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            buffer = parseBuffer(buffer, onChunk)
            onComplete()
            break
          }
          buffer += decoder.decode(value, { stream: true })
          buffer = parseBuffer(buffer, onChunk)
        }
      } catch (error) {
        if (typeof error === 'object' && error !== null && 'detail' in error) {
          onError(new Error(String((error as { detail: unknown }).detail)))
        } else {
          onError(new Error(String(error)))
        }
      }
    },
    []
  )

  return { streamResponse }
}
