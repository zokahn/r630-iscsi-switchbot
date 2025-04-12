# OpenShift Multiboot System Brand Assets Guidelines

This document provides guidelines for the proper usage of the OpenShift Multiboot System brand assets, including logos, banners, and design elements. Consistent usage of these assets helps maintain a professional and unified visual identity across all project documentation and materials.

## Logo

![R630 iSCSI SwitchBot Logo](../../docs_mkdocs/docs/assets/images/r630-iscsi-switchbot-new-logo.png)

### Logo Usage Guidelines

- **Primary Logo**: Always use the provided logo as the primary visual identifier for the project.
- **Clear Space**: Maintain adequate clear space around the logo (minimum of half the logo's height).
- **Minimum Size**: Do not display the logo smaller than 100px in width to maintain legibility.
- **Modifications**: Do not modify, distort, or change the colors of the logo.
- **Background**: The logo works best on white or light backgrounds. When used on dark backgrounds, ensure sufficient contrast.

### Logo Placement

- **Documentation Headers**: Position the logo at the top of documentation pages, centered or aligned left.
- **README Files**: Place the logo prominently at the top of README files, preferably centered.
- **Web Interfaces**: Display the logo in the top navigation bar or header section.
- **Print Materials**: Position the logo on the cover page or header section.

## Banner

![R630 iSCSI SwitchBot Banner](../../docs_mkdocs/docs/assets/images/r630-iscsi-switchbot-banner.png)

### Banner Usage Guidelines

- **Purpose**: Use the banner for main documentation pages, presentations, and marketing materials.
- **Dimensions**: Maintain the aspect ratio of 5:1 when displaying the banner.
- **Placement**: Position the banner at the top of main documentation pages or title slides.
- **Cropping**: Do not crop or modify the banner's content.

## Color Palette

The OpenShift Multiboot System uses a color palette based on Red Hat brand colors:

### Primary Colors

- **Red Hat Red**: #EE0000
  - Use for primary buttons, important notifications, and key highlights
- **Black**: #000000
  - Use for text, icons, and secondary UI elements

### Secondary Colors

- **Dark Gray**: #333333
  - Use for secondary text and UI elements
- **Light Gray**: #CCCCCC
  - Use for backgrounds, dividers, and tertiary UI elements
- **White**: #FFFFFF
  - Use for backgrounds and text on dark elements

## Typography

- **Primary Font**: Red Hat Display and Red Hat Text for headings and body text
- **Fallback Font**: Sans-serif fonts (Arial, Helvetica)
- **Code Font**: Monospace fonts (Consolas, Monaco, Courier New)

## Design Principles

1. **Clarity**: Ensure all visual elements communicate clearly and effectively.
2. **Consistency**: Maintain consistent usage of visual elements across all materials.
3. **Professionalism**: Present a professional and polished appearance.
4. **Red Hat Identity**: Align with Red Hat brand guidelines while maintaining the project's unique identity.
5. **Technical Focus**: Emphasize the technical nature of the project through clean, precise design.

## Implementation Guidelines

### Documentation Pages

- Position the banner at the top of main documentation pages (README, landing pages).
- Display the logo beneath the banner, centered with appropriate spacing.
- Use the logo (without the banner) for secondary documentation pages.

### README Files

```markdown
<div align="center">
  <img src="path/to/banner.png" alt="R630 iSCSI SwitchBot Banner" width="100%">
  
  # OpenShift Multiboot System
  
  <img src="path/to/logo.png" alt="R630 iSCSI SwitchBot Logo" width="250">
</div>
```

### Web Interfaces

- Use the logo in the top navigation bar.
- Consider using the banner for the login or landing page.
- Incorporate the color palette in UI elements.

## File Formats and Sizes

- **Logo**: Available in PNG format (transparent background) at 1024x1024 pixels.
- **Banner**: Available in PNG format at 1792x1024 pixels.
- **Favicon**: Use the logo as a favicon for web interfaces at 32x32 pixels.

## Usage Examples

### Documentation Header

```markdown
<div align="center">
  <img src="docs/assets/images/r630-iscsi-switchbot-banner.png" alt="R630 iSCSI SwitchBot Banner" width="100%">
  
  # OpenShift Multiboot System
  
  <img src="docs/assets/images/r630-iscsi-switchbot-new-logo.png" alt="R630 iSCSI SwitchBot Logo" width="250">
</div>
```

### Web Interface

```html
<header class="main-header">
  <div class="logo-container">
    <img src="assets/images/r630-iscsi-switchbot-new-logo.png" alt="R630 iSCSI SwitchBot Logo" width="50">
  </div>
  <nav class="main-nav">
    <!-- Navigation items -->
  </nav>
</header>
```

## Contact

For questions about brand asset usage or to request additional formats or variations, please contact the project maintainers.
