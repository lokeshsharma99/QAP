import {
  QapIcon,
  AgnoIcon,
  UserIcon,
  AgentIcon,
  ReasoningIcon,
  ReferencesIcon
} from './custom-icons'
import { IconTypeMap } from './types'
import {
  RefreshCw,
  Edit,
  Save,
  X,
  ArrowDown,
  Send,
  Download,
  Hammer,
  Check,
  ChevronDown,
  ChevronUp,
  Trash,
  FileText,
  BookOpen
} from 'lucide-react'
import { PlusIcon } from '@radix-ui/react-icons'

export const ICONS: IconTypeMap = {
  qap: QapIcon,
  agno: AgnoIcon,
  user: UserIcon,
  agent: AgentIcon,
  'open-ai': AgnoIcon, // placeholder — replace with actual logos if needed
  mistral: AgnoIcon,
  gemini: AgnoIcon,
  aws: AgnoIcon,
  azure: AgnoIcon,
  anthropic: AgnoIcon,
  groq: AgnoIcon,
  fireworks: AgnoIcon,
  deepseek: AgnoIcon,
  cohere: AgnoIcon,
  ollama: AgnoIcon,
  xai: AgnoIcon,
  sheet: FileText,
  reasoning: ReasoningIcon,
  references: ReferencesIcon,
  refresh: RefreshCw,
  edit: Edit,
  save: Save,
  x: X,
  'arrow-down': ArrowDown,
  send: Send,
  download: Download,
  hammer: Hammer,
  check: Check,
  'chevron-down': ChevronDown,
  'chevron-up': ChevronUp,
  'plus-icon': PlusIcon,
  trash: Trash
}
