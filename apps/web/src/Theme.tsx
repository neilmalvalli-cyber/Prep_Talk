import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
import {Moon,Sun} from 'lucide-react'
type Theme='light'|'dark'
const ThemeContext=createContext<{theme:Theme;toggle:()=>void}>({theme:'light',toggle:()=>{}})
export function ThemeProvider({children}:{children:ReactNode}){
 const [theme,setTheme]=useState<Theme>(()=>document.documentElement.dataset.theme==='dark'?'dark':'light')
 useEffect(()=>{
  document.documentElement.dataset.theme=theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#202523':'#e6e9e4')
 },[theme])
 useEffect(()=>{const sync=(event:StorageEvent)=>{if(event.key==='fieldnote-theme')setTheme(event.newValue==='dark'?'dark':event.newValue==='light'?'light':matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync)},[])
 function toggle(){const next=theme==='light'?'dark':'light';setTheme(next);try{localStorage.setItem('fieldnote-theme',next)}catch{/* The theme still works when browser storage is disabled. */}}
 return <ThemeContext.Provider value={{theme,toggle}}>{children}</ThemeContext.Provider>
}
export const useTheme=()=>useContext(ThemeContext)
export function ThemeToggle(){const {theme,toggle}=useTheme();return <button className="theme-toggle" type="button" onClick={toggle} aria-label={`Switch to ${theme==='light'?'dark':'light'} mode`} title={`Switch to ${theme==='light'?'dark':'light'} mode`}>{theme==='light'?<Moon size={18}/>:<Sun size={18}/>}<span>{theme==='light'?'Dark mode':'Light mode'}</span></button>}
