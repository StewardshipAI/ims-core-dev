pub enum SettingValue {
    Toggle(bool),
    Slider(u8, u8, u8), // Current, Min, Max
    Select(Vec<String>, usize), // Options, Selected Index
}

pub struct SettingItem {
    pub key: String,
    pub label: String,
    pub description: String,
    pub value: SettingValue,
}

pub struct SettingsState {
    pub items: Vec<SettingItem>,
    pub selected_index: usize,
}

impl SettingsState {
    pub fn new() -> Self {
        Self {
            items: vec![
                SettingItem {
                    key: "global_auto_scroll".to_string(),
                    label: "Global Auto-Scroll".to_string(),
                    description: "Automatically scroll to the bottom of live streams.".to_string(),
                    value: SettingValue::Toggle(true),
                },
                SettingItem {
                    key: "theme_cursor".to_string(),
                    label: "Vendor Cursor".to_string(),
                    description: "Use the model's logo as the active typing cursor.".to_string(),
                    value: SettingValue::Toggle(true),
                },
                // ADD NEW SETTINGS HERE: Claude can just append to this list
            ],
            selected_index: 0,
        }
    }
}