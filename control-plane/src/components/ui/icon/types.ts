import { type ElementType } from 'react'

export type IconType =
  | 'qap'
  | 'agno'
  | 'user'
  | 'agent'
  | 'open-ai'
  | 'mistral'
  | 'gemini'
  | 'aws'
  | 'azure'
  | 'anthropic'
  | 'groq'
  | 'fireworks'
  | 'deepseek'
  | 'cohere'
  | 'ollama'
  | 'xai'
  | 'sheet'
  | 'reasoning'
  | 'references'
  | 'refresh'
  | 'edit'
  | 'save'
  | 'x'
  | 'arrow-down'
  | 'send'
  | 'download'
  | 'hammer'
  | 'check'
  | 'chevron-down'
  | 'chevron-up'
  | 'plus-icon'
  | 'trash'

export interface IconProps {
  type: IconType
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'dot' | 'xxs' | 'default'
  className?: string
  color?: string
  disabled?: boolean
}

export type IconTypeMap = {
  [key in IconType]: ElementType
}
