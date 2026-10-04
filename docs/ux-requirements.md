# UX requirements

## Principles

1. **Phone-first** - most users have Android/iOS browsers, not laptops.  
2. **Icons before text** - literacy and language vary.  
3. **Large touch targets** - minimum ~48×48 CSS px.  
4. **Progressive disclosure** - home -> category -> item.  
5. **Honest offline** - show "Offline OK" and content age.  
6. **Voice optional** - browser TTS when enabled.  

## Portal

- Categories: Emergency, Health, Education, Farm, Weather, Maps  
- Language switcher: en, fr, es, ar, sw, hi, pt (RTL for Arabic)  
- Age chips: "2h ago"; stale warning after `freshness_hours`  
- Legal banner always visible  

## Admin

- PIN gated  
- Power SOC + mode  
- Disk free  
- Package count  
- Signal message  
- Plugin list  
- Legal reminder  

## Captive portal

- Redirect common OS connectivity checks to `/`  
- Document HTTP-only limitations on some phones  

## Accessibility

- Focus visible outlines  
- `prefers-reduced-motion` respected  
- High contrast dark theme default (sunlight + night)  
- Avoid text-only critical actions  

## Non-goals

- Fancy app stores  
- User accounts / social feeds  
- Auto-playing video on home  
