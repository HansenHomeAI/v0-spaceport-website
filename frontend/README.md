# Spaceport Frontend

This directory contains the frontend code for the Spaceport drone photography platform.

## Development

To run the development server:

```bash
npm run dev
```

This will start a local server at `http://localhost:8000`.

## Structure

```
frontend/
├── public/          # Static files served directly
│   ├── index.html   # Main HTML file
│   └── assets/      # Images, logos, etc.
├── src/             # Source code
│   ├── styles.css   # Stylesheets
│   └── script.js    # JavaScript code
└── package.json     # Frontend dependencies
```

## Assets

- **Logos**: Located in `public/assets/logos/`
- **Images**: Located in `public/assets/images/`

## Future Improvements

Consider adding:
- A modern build tool (Vite, Webpack, or Parcel)
- TypeScript for better type safety
- A CSS framework or preprocessor
- Module bundling and tree shaking
- Hot reload for development 