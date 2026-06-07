export type Status = 'normal' | 'low' | 'empty' | 'broken' | 'missing' | 'idle' | 'archived'

export interface ApiEnvelope<T> {
  success: boolean
  data: T
  message?: string
  error?: {
    code: string
    message: string
  }
}

export interface Category {
  id: number
  name: string
  slug: string
  code_prefix: string
  parent_id: number | null
  sort_order: number
  description?: string | null
  is_system: boolean
  created_at?: string
  updated_at?: string
  children?: Category[]
}

export interface LocationNode {
  id: number
  name: string
  code: string
  full_code: string
  parent_id: number | null
  type: string | null
  description: string | null
  sort_order: number
  layout_type?: 'grid' | 'row' | null
  layout_rows?: number | null
  layout_columns?: number | null
  appearance_color?: string | null
  appearance_icon?: 'box' | 'drawer' | 'shelf' | null
  is_slot?: boolean
  slot_key?: string | null
  slot_order?: number | null
  children?: LocationNode[]
}

export interface LocationFormPayload {
  name: string
  code?: string
  parent_code?: string | null
  type?: string | null
  description?: string | null
  sort_order?: number
}

export interface Item {
  id: number
  code: string
  name: string
  category_id: number | null
  location_id: number | null
  location_text: string | null
  location_display?: string | null
  quantity: string | number | null
  unit: string | null
  status: Status
  description: string | null
  need_restock: boolean
  is_favorite: boolean
  cover_attachment_id: number | null
  is_archived: boolean
}

export interface ContainerLayoutPayload {
  layout_type: 'grid' | 'row'
  layout_rows: number
  layout_columns: number
  appearance_color: string
  appearance_icon: 'box' | 'drawer' | 'shelf'
}

export interface ContainerCreatePayload extends ContainerLayoutPayload {
  name: string
  code: string
  parent_code?: string | null
  type?: string | null
  description?: string | null
  sort_order?: number
}

export interface SlotAssignment {
  item_code: string
  slot_key: string
}

export interface ContainerBoardSlot {
  location: LocationNode
  item: Item | null
}

export interface ContainerBoard {
  container: LocationNode
  slots: ContainerBoardSlot[]
}

export interface ItemFormPayload {
  name: string
  category?: string | number | null
  category_id?: number | null
  location_text?: string | null
  location_code?: string | null
  quantity?: number | null
  unit?: string | null
  status?: Status
  description?: string | null
  attributes?: Array<{
    name: string
    key: string
    value?: string | null
    value_type?: string | null
    unit?: string | null
  }>
  tags?: string[]
  note?: string | null
  need_restock?: boolean
  is_favorite?: boolean
}

export interface AttributeDefinition {
  id: number
  category_id: number
  name: string
  key: string
  field_type: string
  unit: string | null
  options_json: string | null
  required: boolean
  sort_order: number
  is_enabled: boolean
}

export interface ItemAttribute {
  id: number
  item_id: number
  name: string
  key: string
  value: string | null
  unit: string | null
}

export interface Tag {
  id: number
  name: string
  slug: string | null
}

export interface Note {
  id: number
  content: string
  note_type: string
  source: string
  created_at: string
}

export interface Attachment {
  id: number
  item_id: number
  attachment_type: string
  original_name: string
  stored_name?: string
  file_path: string
  thumbnail_path?: string | null
  mime_type: string | null
  size_bytes: number | null
  description?: string | null
  is_cover: boolean
  is_deleted?: boolean
  created_at?: string
}

export interface Backup {
  id: number
  backup_id: string
  file_path: string
  size_bytes: number | null
  include_uploads: boolean
  note: string | null
  status: string
  created_at: string
}

export interface StatsOverview {
  item_count: number
  archived_item_count: number
  low_stock_count: number
  restock_count: number
  favorite_count: number
  unlocated_count: number
  uncategorized_count: number
  attachment_count: number
  category_counts: Array<{
    category_id: number
    name: string
    count: number
  }>
  location_counts: Array<{
    location_id: number
    name: string
    full_code: string
    count: number
  }>
}

export type ExtensionSettingType = 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'secret' | 'path'

export interface ExtensionSettingOption {
  label: string
  value: string
}

export interface ExtensionSettingField {
  type: ExtensionSettingType
  label: string
  required?: boolean
  default?: unknown
  options?: ExtensionSettingOption[]
  min?: number | null
  max?: number | null
}

export interface ExtensionContribution {
  extension_id: string
  extension_name: string
  place: string
  type: string
  label: string
  action: string
  requires?: string[]
}

export interface ExtensionManifest {
  id: string
  name: string
  description?: string | null
  version: string
  api_version: string
  enabled: boolean
  configured: boolean
  settings: {
    schema: Record<string, ExtensionSettingField>
  }
  settings_values: Record<string, unknown>
  contributions: Array<Omit<ExtensionContribution, 'extension_id' | 'extension_name'>>
}
