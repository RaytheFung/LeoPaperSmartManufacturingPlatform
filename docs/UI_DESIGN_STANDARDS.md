# UI Design Standards & Guidelines
## Smart Manufacturing Platform

---

## 🎨 Design Philosophy

### Core Principles
1. **Data-First Design**: Information clarity takes precedence over decoration
2. **Progressive Disclosure**: Show essential info first, details on demand
3. **Consistency**: Uniform patterns across all modules
4. **Accessibility**: Clear contrast, readable fonts, intuitive navigation
5. **Performance**: Fast loading, responsive interactions

---

## 🎯 Visual Hierarchy

### Page Structure
```
┌─────────────────────────────────────┐
│         Header (Title + Status)      │
├─────────────┬───────────────────────┤
│   Sidebar   │                       │
│   (200px)   │    Main Content       │
│             │    (Responsive)       │
│   - Stats   │                       │
│   - Nav     │    - Tabs/Sections    │
│   - Info    │    - Data Display     │
│             │    - Actions          │
└─────────────┴───────────────────────┘
```

### Content Prioritization
1. **Primary**: Key metrics, alerts, actions
2. **Secondary**: Supporting data, trends
3. **Tertiary**: Configuration, settings (collapsible)

---

## 🎨 Color Palette

### Primary Colors
- **Brand Blue**: `#667eea` - Primary actions, headers
- **Success Green**: `#4CAF50` - Positive metrics, confirmations
- **Warning Orange**: `#ff9800` - Alerts, attention needed
- **Error Red**: `#f44336` - Critical issues, stops
- **Info Blue**: `#2196F3` - Information, tips

### Background Colors
- **Primary BG**: `#ffffff` - Main content
- **Secondary BG**: `#f8f9fa` - Cards, containers
- **Tertiary BG**: `#e1e4e8` - Borders, dividers
- **Highlight BG**: `#f0f7ff` - Selected/hover states

### Text Colors
- **Primary Text**: `#333333` - Main content
- **Secondary Text**: `#555555` - Labels, descriptions
- **Muted Text**: `#999999` - Timestamps, metadata
- **Light Text**: `#ffffff` - On dark backgrounds

---

## 📐 Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
             "Helvetica Neue", Arial, sans-serif;
```

### Size Scale
- **H1**: 32px - Page titles
- **H2**: 24px - Section headers  
- **H3**: 20px - Subsection headers
- **H4**: 16px - Card titles
- **Body**: 14px - Regular text
- **Small**: 12px - Captions, labels

### Font Weights
- **Bold**: 600-700 - Headers, emphasis
- **Medium**: 500 - Subheaders
- **Regular**: 400 - Body text

---

## 📦 Component Standards

### Metrics Cards
```python
st.metric(
    label="Metric Name",
    value="Primary Value",
    delta="Change",
    delta_color="normal/inverse"
)
```
**Styling**: 
- Background: `#f8f9fa`
- Border: `1px solid #e1e4e8`
- Border-radius: `12px`
- Padding: `15px`
- Shadow: `0 2px 4px rgba(0,0,0,0.08)`

### Data Tables
```python
st.dataframe(
    data,
    use_container_width=True,
    hide_index=True,
    column_config={...}
)
```
**Requirements**:
- No text truncation (full text visible)
- Sortable columns
- Responsive width
- Zebra striping for readability

### Buttons
```python
st.button(
    "Action Text",
    type="primary/secondary",
    use_container_width=True
)
```
**Styling**:
- Height: `44px` minimum
- Border-radius: `10px`
- Font-weight: `600`
- Hover: Transform & shadow effect

### Alerts/Info Boxes
- **Success**: Green background `#d4edda`
- **Warning**: Yellow background `#fff3cd`
- **Error**: Red background `#f8d7da`
- **Info**: Blue background `#d1ecf1`

### Charts & Graphs
- **Consistent color scheme** across all charts
- **Always include** target lines where applicable
- **Interactive tooltips** with full information
- **Responsive sizing** to container

---

## 📱 Responsive Design

### Breakpoints
- **Desktop**: > 1200px (default)
- **Tablet**: 768px - 1200px
- **Mobile**: < 768px (not primary, but consider)

### Column Layouts
```python
# Desktop: Side by side
col1, col2 = st.columns([2, 1])

# Mobile consideration: Stack vertically
# (Streamlit handles automatically)
```

### Best Practices
1. Use `use_container_width=True` for responsive components
2. Avoid fixed pixel widths except for sidebar
3. Test with browser zoom 75% - 125%

---

## 🔄 Interaction Patterns

### Progressive Disclosure
```python
with st.expander("View Details", expanded=False):
    # Detailed content here
```

### Loading States
```python
with st.spinner("Loading data..."):
    # Long operation
```

### Feedback
- **Success**: Show confirmation with metrics
- **Error**: Display clear error message with recovery action
- **Progress**: Use progress bars for long operations

---

## ⚡ Performance Guidelines

### Data Display
1. **Pagination**: Limit initial display to 100 rows
2. **Lazy Loading**: Load details on demand
3. **Caching**: Use `@st.cache_data` for expensive operations
4. **Optimization**: Pre-aggregate data where possible

### Visual Performance
1. **Minimize CSS**: Inline only critical styles
2. **Optimize Images**: Use appropriate formats and sizes
3. **Reduce Redraws**: Batch UI updates

---

## 🎯 Module-Specific Guidelines

### Dashboard Module
- **Grid Layout**: 2-4 metrics per row
- **Time Selector**: Prominent position
- **Refresh Button**: Top-right corner

### ETL Module
- **Status Indicators**: Traffic light system
- **Progress Tracking**: Linear progress bar
- **File Lists**: Sortable tables with actions

### ML Module
- **Model Comparison**: Side-by-side table
- **Feature Importance**: Horizontal bar chart
- **Predictions**: Clear input → output flow

### Analytics Module
- **Charts First**: Visualizations above tables
- **Filters**: Sidebar or top of page
- **Export Options**: Bottom of data sections

### Maintenance Module
- **Timeline View**: Gantt-style chart
- **Machine Cards**: Grid layout with status badges
- **Quick Actions**: Floating action buttons

---

## 🚫 UI Anti-Patterns to Avoid

1. **Truncated Text**: Never use ellipsis (...) for critical data
2. **Nested Scrolling**: Avoid scrollable areas within scrollable pages
3. **Invisible Actions**: All buttons must be visible without scrolling
4. **Overwhelming Dashboards**: Limit to 6-8 key metrics per view
5. **Inconsistent Spacing**: Maintain uniform margins and padding
6. **Poor Contrast**: Ensure WCAG AA compliance (4.5:1 minimum)
7. **Hardcoded Values**: Use configuration files for thresholds

---

## ✅ Checklist for UI Review

### Before Release
- [ ] All text is fully visible (no truncation)
- [ ] Colors follow the defined palette
- [ ] Responsive on 1366x768 and up
- [ ] Loading states for all async operations
- [ ] Error handling with user guidance
- [ ] Consistent component usage
- [ ] No hardcoded demo data in production
- [ ] Performance: Page loads < 3 seconds
- [ ] Accessibility: Keyboard navigation works
- [ ] Export functionality for all data views

### Testing Requirements
- [ ] Test with real data (not just demo)
- [ ] Verify on multiple browsers (Chrome, Firefox, Safari)
- [ ] Check different screen resolutions
- [ ] Validate color contrast ratios
- [ ] Ensure mobile responsiveness

---

## 📚 Implementation Examples

### Standard Page Template
```python
def render_module():
    # Custom CSS
    st.markdown(STANDARD_CSS, unsafe_allow_html=True)
    
    # Header
    st.title("🎯 Module Name")
    st.markdown("**Brief description of module purpose**")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Quick Stats")
        # Key metrics here
    
    # Main content with tabs
    tab1, tab2, tab3 = st.tabs(["Main", "Details", "Settings"])
    
    with tab1:
        # Primary functionality
        pass
```

### Standard Metric Display
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="Efficiency",
        value=f"{value:.2f} kWh/unit",
        delta=f"{change:+.2f}",
        delta_color="inverse" if change > 0 else "normal"
    )
```

### Standard Data Table
```python
st.dataframe(
    data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "column_name": st.column_config.TextColumn(
            "Display Name",
            width="medium",
            help="Tooltip text"
        )
    }
)
```

---

## 🔄 Version History

- **v1.0** (2024-12-25): Initial design standards
- **v1.1** (TBD): Add dark mode support
- **v1.2** (TBD): Mobile-first responsive updates

---

## 📞 Design Support

For design questions or suggestions:
- Review this document first
- Check implementation examples
- Consult with team lead for exceptions
- Document any approved deviations

---

*Last Updated: December 2024*
*Maintained by: Smart Manufacturing Team*