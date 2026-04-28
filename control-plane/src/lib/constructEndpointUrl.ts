export const constructEndpointUrl = (value: string | null | undefined): string => {
  if (!value) return ''

  if (value.startsWith('http://') || value.startsWith('https://')) {
    return decodeURIComponent(value)
  }

  if (
    value.startsWith('localhost') ||
    /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/.test(value)
  ) {
    return `http://${decodeURIComponent(value)}`
  }

  return `https://${decodeURIComponent(value)}`
}
