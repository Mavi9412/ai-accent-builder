# AI ACCENT - React Dashboard

A beautiful responsive dashboard for an AI-powered language learning platform, built with React.

## Features

- Modern, responsive UI with beautiful animations and transitions
- Interactive charts powered by Chart.js
- Collapsible sidebar navigation
- User progress tracking and analytics
- Module cards with progress indicators

## Project Structure

```
src/
├── components/
│   ├── Dashboard.js       # Main dashboard container component
│   ├── Dashboard.css      # Styles for all dashboard components
│   ├── Sidebar.js         # Collapsible sidebar navigation
│   ├── StatsGrid.js       # User statistics grid component
│   ├── ModulesGrid.js     # Learning modules grid component
│   ├── ModuleCard.js      # Individual module card component
│   └── AnalyticsSection.js # Charts and analytics component
├── App.js                 # Main app with routing
└── index.js               # Entry point
```

## Dependencies

- React 18.2.0
- React Router 6.11.2
- Chart.js 4.3.0
- Font Awesome (via CDN)
- Google Fonts: Poppins (via CDN)

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```
   npm install
   ```
3. Add the required CDN links to your `public/index.html`:
   ```html
   <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
   ```
4. Start the development server:
   ```
   npm start
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Customization

- Color variables are defined in `Dashboard.css` under the `:root` selector
- Chart configurations can be modified in `AnalyticsSection.js`
- Component data is currently hardcoded but can be easily connected to an API

## Responsive Design

The dashboard is fully responsive and adapts to different screen sizes:
- Desktop: Full layout with sidebar and 4-column charts
- Tablet: Collapsed sidebar and 2-column layout
- Mobile: Stacked layout with optimized spacing
