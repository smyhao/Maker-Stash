export const MSLOC_PREFIX = 'MSLOC:'

export function toMsloc(fullCode: string) {
  return `${MSLOC_PREFIX}${fullCode}`
}

export function parseMsloc(value: string) {
  const text = value.trim()
  if (!text.startsWith(MSLOC_PREFIX)) return null
  const fullCode = text.slice(MSLOC_PREFIX.length).trim()
  return fullCode ? fullCode : null
}
