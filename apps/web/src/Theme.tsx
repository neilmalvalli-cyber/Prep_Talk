import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
import {Moon,Sun} from 'lucide-react'
type Theme='light'|'dark'
const STORAGE_KEY='preptalk-theme'
const ThemeContext=createContext<{theme:Theme;toggle:()=>void}>({theme:'light',toggle:()=>{}})
export function ThemeProvider({children}:{children:ReactNode}){
 const [theme,setTheme]=useState<Theme>(()=>document.documentElement.dataset.theme==='dark'?'dark':'light')
 useEffect(()=>{
  document.documentElement.dataset.theme=theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#0B1418':'#F0F1F4')
 },[theme])
 useEffect(()=>{const sync=(event:StorageEvent)=>{if(event.key===STORAGE_KEY)setTheme(event.newValue==='dark'?'dark':event.newValue==='light'?'light':matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync)},[])
 function toggle(){const next=theme==='light'?'dark':'light';setTheme(next);try{localStorage.setItem(STORAGE_KEY,next)}catch{/* The theme still works when browser storage is disabled. */}}
 return <ThemeContext.Provider value={{theme,toggle}}>{children}</ThemeContext.Provider>
}
// The interview room is always dark; glass, sphere and editor read the scoped theme.
export function ThemeScope({theme,children}:{theme:Theme;children:ReactNode}){
 const parent=useContext(ThemeContext)
 return <ThemeContext.Provider value={{theme,toggle:parent.toggle}}>{children}</ThemeContext.Provider>
}
export const useTheme=()=>useContext(ThemeContext)
export function ThemeToggle(){const {theme,toggle}=useTheme();return <button className="icon-button" type="button" onClick={toggle} aria-label={`Switch to ${theme==='light'?'dark':'light'} mode`} title={`Switch to ${theme==='light'?'dark':'light'} mode`}>{theme==='light'?<Moon size={17}/>:<Sun size={17}/>}</button>}
