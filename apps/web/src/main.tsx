import React from 'react'
import {createRoot} from 'react-dom/client'
import {ThemeProvider} from './Theme'
import App from './App'
import './fonts.css'
import './styles.css'
import './design-system.css'
createRoot(document.getElementById('root')!).render(<React.StrictMode><ThemeProvider><App/></ThemeProvider></React.StrictMode>)
