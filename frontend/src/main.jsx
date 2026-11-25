import React, {useEffect, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {LayoutDashboard, CarFront, Wrench, Package, CalendarDays, ReceiptText, ShieldCheck, Users, LogOut, Search, Plus, RefreshCw, Trash2, Pencil, CheckCircle2, CircleAlert, Menu, ChevronRight, ClipboardList} from 'lucide-react'
import './style.css'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const STATUSES = {REQUESTED:'Demande',DIAGNOSIS:'Diagnostic',REPAIR:'Réparation',COMPLETED:'Terminé',CANCELLED:'Annulé'}
const APPOINTMENT_STATUSES = {PENDING:'En attente',PLANNED:'Planifié',REJECTED:'Refusé',COMPLETED:'Terminé',CANCELLED:'Annulé'}
const NEXT = {REQUESTED:['DIAGNOSIS','CANCELLED'],DIAGNOSIS:['REPAIR','CANCELLED'],REPAIR:['COMPLETED']}
const NAV=[['dashboard','Vue générale',LayoutDashboard],['interventions','Interventions',Wrench],['appointments','Rendez-vous',CalendarDays],['vehicles','Véhicules',CarFront],['parts','Pièces & stock',Package],['mechanics','Mécaniciens',Users],['users','Utilisateurs',Users],['invoices','Factures',ReceiptText],['audit','Journal d’audit',ShieldCheck]]
const DEFINITIONS={
 users:{title:'Utilisateurs',fields:[['name','Nom complet','text'],['email','Adresse e-mail','email'],['password','Mot de passe','password'],['role','Rôle','select']],headers:[['id','ID'],['name','Nom complet'],['email','Email'],['role','Rôle'],['active','Actif']]},
 vehicles:{title:'Véhicules',fields:[['owner_id','Propriétaire (ID)','number'],['plate','Immatriculation','text'],['brand','Marque','text'],['model','Modèle','text'],['year','Année','number']],headers:[['photo','Photo'],['id','ID'],['plate','Immatriculation'],['brand','Marque'],['model','Modèle'],['owner_id','Client ID']]},
 parts:{title:'Pièces détachées',fields:[['sku','Référence SKU','text'],['name','Désignation','text'],['stock','Quantité en stock','number'],['unit_price','Prix unitaire (TND)','number']],headers:[['sku','Référence'],['name','Désignation'],['stock','Stock'],['unit_price','Prix (TND)']]},
 mechanics:{title:'Mécaniciens',fields:[['user_id','Utilisateur mécanicien (ID)','number'],['specialty','Spécialité','text']],headers:[['name','Nom'],['specialty','Spécialité'],['user_id','Utilisateur ID']]},
 appointments:{title:'Rendez-vous',fields:[['vehicle_id','Véhicule','select'],['mechanic_id','Mécanicien','select'],['starts_at','Début','datetime-local'],['ends_at','Fin','datetime-local'],['reason','Motif','text']],headers:[['vehicle_id','Véhicule'],['mechanic_id','Mécanicien'],['starts_at','Début'],['status','Statut']]},
 interventions:{title:'Interventions',fields:[['vehicle_id','Véhicule','select'],['mechanic_id','Mécanicien','select'],['appointment_id','Rendez-vous (facultatif)','select'],['description','Description de la panne','text'],['labor_cost','Main-d’œuvre (TND)','number']],headers:[['id','N°'],['vehicle_id','Véhicule'],['description','Description'],['status','État'],['labor_cost','Main-d’œuvre']]},
 invoices:{title:'Factures',fields:[],headers:[['id','Facture'],['intervention_id','Intervention'],['amount','Montant (TND)'],['status','Paiement']]},
 audit:{title:'Journal d’audit',fields:[],headers:[['created_at','Date'],['user_id','Utilisateur'],['action','Action'],['resource','Ressource'],['resource_id','ID']]}
}

function App(){
 const [token,setToken]=useState(localStorage.getItem('gp_token')||'')
 const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem('gp_user')||'null')}catch{return null}})
 const [page,setPage]=useState('dashboard'),[rows,setRows]=useState([]),[dashboard,setDashboard]=useState({}),[error,setError]=useState(''),[notice,setNotice]=useState(''),[loading,setLoading]=useState(false),[search,setSearch]=useState(''),[statusFilter,setStatusFilter]=useState(''),[dateFilter,setDateFilter]=useState('')
 const [modal,setModal]=useState(null),[values,setValues]=useState({}),[credentials,setCredentials]=useState({email:'',password:''}),[authMode,setAuthMode]=useState('login'),[sidebar,setSidebar]=useState(false)
 const [users,setUsers]=useState([]),[extra,setExtra]=useState(null)
 const [vehiclePhotos,setVehiclePhotos]=useState({}),[selectedVehiclePhoto,setSelectedVehiclePhoto]=useState(null),[photoProcessing,setPhotoProcessing]=useState(false)
  const [vehicles,setVehicles]=useState([]),[mechanics,setMechanics]=useState([]),[parts,setParts]=useState([]),[appointments,setAppointments]=useState([])
  const [reportText,setReportText]=useState(''),[reportNotes,setReportNotes]=useState(''),[reportLoading,setReportLoading]=useState(false),[myTasks,setMyTasks]=useState([])
 const role=user?.role
 const available= NAV.filter(([id])=> role==='ADMIN'||(role==='CLIENT'?['dashboard','interventions','appointments','vehicles','invoices'].includes(id):['dashboard','interventions','appointments','vehicles','parts','invoices'].includes(id)))
 const api=async(path,opts={})=>{
   const res=await fetch(`${BASE}/api${path}`,{...opts,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}),...(opts.headers||{})}})
   let data;try{data=await res.json()}catch{data={detail:`Erreur serveur (${res.status})`}}
   if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)||`HTTP ${res.status}`)
   return data
 }
 const fetchPhotos=async(vehicleRows)=>{
   const pairs=await Promise.all(vehicleRows.map(async(v)=>{
     try{const result=await api(`/vehicles/${v.id}/photo`);return [v.id,result.image]}
     catch{return [v.id,null]}
   }))
   setVehiclePhotos(Object.fromEntries(pairs))
 }
 // Redimensionne et compresse sur le navigateur avant de transmettre la photo.
 const compressVehicleImage=async(file)=>{
   const MAX_BYTES=3_000_000;
   const MAX_SOURCE_BYTES=25_000_000;
   if(file.size>MAX_SOURCE_BYTES)throw new Error('Photo trop volumineuse : maximum 25 Mo avant compression.');
   const image=await createImageBitmap(file);
   try{
     if(image.width*image.height>35_000_000)throw new Error('Dimensions de photo trop grandes.');
     const maxSide=1600;
     const ratio=Math.min(1,maxSide/Math.max(image.width,image.height));
     const canvas=document.createElement('canvas');
     canvas.width=Math.max(1,Math.round(image.width*ratio));
     canvas.height=Math.max(1,Math.round(image.height*ratio));
     const ctx=canvas.getContext('2d');
     if(!ctx)throw new Error('Compression impossible dans ce navigateur.');
     // Fond blanc : les PNG transparents ne deviennent pas noirs en JPEG.
     ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);
     ctx.drawImage(image,0,0,canvas.width,canvas.height);
     for(const quality of [0.85,0.72,0.58,0.42]){
       const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',quality));
       if(blob && blob.size<=MAX_BYTES){
         return await new Promise((resolve,reject)=>{
           const reader=new FileReader();
           reader.onload=()=>resolve(String(reader.result));
           reader.onerror=()=>reject(new Error('Impossible de lire la photo compressée.'));
           reader.readAsDataURL(blob);
         });
       }
     }
     throw new Error('Impossible de réduire cette photo sous 3 Mo. Choisissez une image plus petite.');
   }finally{image.close()}
 }
 const selectVehicleImage=async(event)=>{
   const file=event.target.files?.[0];
   if(!file){setSelectedVehiclePhoto(null);return}
   if(!['image/jpeg','image/png','image/webp'].includes(file.type)){
     setError('Choisissez une photo JPG, PNG ou WEBP.');event.target.value='';return;
   }
   setPhotoProcessing(true);setError('');setSelectedVehiclePhoto(null);
   try{
     const result=await compressVehicleImage(file);
     setSelectedVehiclePhoto(result);
     setNotice('Photo optimisée et prête à enregistrer.');
   }catch(e){setError(e.message);event.target.value=''}
   finally{setPhotoProcessing(false)}
 }
 const flash=(message)=>{setNotice(message);setError('')}
 const load=async()=>{
  if(!token)return
  setLoading(true);setError('')
  try{
   const [d,data]=await Promise.all([api('/dashboard'),page==='dashboard'?Promise.resolve([]):api(`/${page}`)])
   setDashboard(d);setRows(data)
   if(page==='vehicles')await fetchPhotos(data)
   if(page==='dashboard'&&role==='MECANICIEN'){
     setMyTasks(await api('/interventions'))
   }

   if(role==='ADMIN'&&['vehicles','mechanics','users','appointments','interventions','invoices','audit'].includes(page))setUsers(page==='users'?data:await api('/users'))
    // Les listes des rendez-vous et interventions utilisent les vrais ID de l'API.
    if(['appointments','interventions','invoices'].includes(page)){
      const [vehicleList,mechanicList,partList]=await Promise.all([
        api('/vehicles'),
        api('/mechanics'),
        page==='interventions' && role!=='CLIENT' ? api('/parts') : Promise.resolve([])
      ])
      setVehicles(vehicleList);setMechanics(mechanicList);setParts(partList)
      if(page==='interventions'){
        const appointmentList=await api('/appointments')
        setAppointments(appointmentList)
      }
    }
  }catch(e){setError(e.message)}finally{setLoading(false)}
 }
 useEffect(()=>{load()},[token,page])
 // Actualisation des alertes de stock sur le tableau de bord ADMIN.
 useEffect(()=>{
  if(!token || role!=='ADMIN' || page!=='dashboard')return;
  let alive=true;
  const refresh=async()=>{try{const current=await api('/dashboard');if(alive)setDashboard(current)}catch{/* l'actualisation manuelle reste disponible */}};
  const timer=window.setInterval(refresh,15000);
  return ()=>{alive=false;window.clearInterval(timer)};
 },[token,role,page]);
 // Le client voit automatiquement l'acceptation du rendez-vous sans recharger la page.
 useEffect(()=>{
   if(!token || role!=='CLIENT' || page!=='appointments')return;
   let active=true;
   const timer=window.setInterval(async()=>{
     try{
       const current=await api('/appointments');
       if(active)setRows(current);
     }catch{/* La prochaine actualisation réessaiera. */}
   },12000);
   return ()=>{active=false;window.clearInterval(timer)};
 },[token,role,page]);
 const logout=()=>{localStorage.removeItem('gp_token');localStorage.removeItem('gp_user');setToken('');setUser(null);setPage('dashboard');setModal(null)}
 const auth=async(e)=>{
  e.preventDefault();setError('');setLoading(true)
  try{
   // FastAPI refuses extra fields: Login accepts ONLY email and password.
   // A previous registration leaves 'name' in credentials, so build each payload explicitly.
   const loginPayload = {email:(credentials.email||'').trim().toLowerCase(),password:credentials.password||''};
   if(authMode==='register'){
    await api('/auth/register',{method:'POST',body:JSON.stringify({name:(credentials.name||'').trim(),...loginPayload})});
   }
   // Auto-connect after registration; also handles ordinary login.
   const res=await api('/auth/login',{method:'POST',body:JSON.stringify(loginPayload)});
   localStorage.setItem('gp_token',res.access_token);
   localStorage.setItem('gp_user',JSON.stringify(res.user));
   setToken(res.access_token);setUser(res.user);setPage('dashboard');
   setCredentials({email:loginPayload.email,password:''});
   flash(`Bienvenue ${res.user.name}`)
  }catch(e){setError(e.message)}finally{setLoading(false)}
 }
 const startForm=(edit=null)=>{setSelectedVehiclePhoto(null);setExtra(null);setValues(edit?{...edit}:{...Object.fromEntries((DEFINITIONS[page]?.fields||[]).map(([k])=>[k,''])),...(page==='users'?{role:'CLIENT'}:{})});setModal(edit?{type:'edit',id:edit.id}:{type:'new'})}
 const submit=async(e)=>{
  e.preventDefault();setLoading(true);setError('')
  const fields=DEFINITIONS[page].fields
  const payload=Object.fromEntries(fields.map(([key,_,kind])=>{
    let val=values[key];if(val===''||val===undefined||val===null)val=null
    if(val!==null&&(kind==='number'||kind==='select'&&['vehicle_id','mechanic_id','appointment_id'].includes(key)))val=Number(val)
    if(val!==null&&kind==='datetime-local')val=new Date(val).toISOString()
    return [key,val]
  }))
  if(page==='vehicles'&&role==='CLIENT')delete payload.owner_id
  if(page==='mechanics'&&payload.specialty===null)payload.specialty='Général'
  if(page==='users'){payload.email=String(payload.email||'').trim().toLowerCase();payload.name=String(payload.name||'').trim()}
  try{
   const saved=await api(`/${page}${modal.type==='edit'?`/${modal.id}`:''}`,{method:modal.type==='edit'?'PUT':'POST',body:JSON.stringify(payload)})
   if(page==='vehicles' && selectedVehiclePhoto){
     const vehicleId=modal.type==='edit'?modal.id:saved.id
     try{
       await api(`/vehicles/${vehicleId}/photo`,{method:'PUT',body:JSON.stringify({image:selectedVehiclePhoto})})
     }catch(photoError){
       setModal(null)
       setSelectedVehiclePhoto(null)
       await load()
       throw new Error(`Véhicule enregistré, mais photo non ajoutée : ${photoError.message}`)
     }
   }
   setSelectedVehiclePhoto(null)
   setModal(null);flash('Enregistrement effectué');await load()
  }catch(e){setError(e.message)}finally{setLoading(false)}
 }
 const remove=async(id)=>{
  if(!confirm('Supprimer cet élément ? Cette action est définitive.'))return
  try{await api(`/${page}/${id}`,{method:'DELETE'});flash('Élément supprimé');await load()}catch(e){setError(e.message)}
 }
 const action=async(fn)=>{try{setError('');await fn();setModal(null);flash('Opération effectuée');await load()}catch(e){setError(e.message)}}
 // Compte rendu du mécanicien : seules ses interventions peuvent être modifiées.
 const openReport=async(item)=>{
   setError('');setReportText('');setReportNotes('');setReportLoading(true)
   try{
     const response=await api(`/interventions/${item.id}/report`)
     setReportText(response.work_done||'');setReportNotes(response.observations||'')
   }catch(e){if(!String(e.message).includes('404')&&!e.message.includes('non encore saisi'))setError(e.message)}
   finally{setReportLoading(false);setExtra({kind:'report',item});setModal({type:'extra'})}
 }
 const saveReport=async(e)=>{
   e.preventDefault();
   await action(()=>api(`/interventions/${extra.item.id}/report`,{method:'PUT',body:JSON.stringify({work_done:reportText,observations:reportNotes})}))
 }
 // Génère une facture imprimable à partir des données réelles de l'API.
 const printInvoice=async(invoice)=>{
  const popup=window.open('', '_blank');
  if(!popup){setError('Autorisez les fenêtres pop-up pour imprimer la facture.');return}
  popup.document.write('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Préparation de la facture</title><body><p>Chargement de la facture...</p></body></html>');
  const esc=(value)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=(value)=>Number(value||0).toLocaleString('fr-TN',{minimumFractionDigits:2,maximumFractionDigits:2})+' TND';
  try{
   const [interventionsList,vehicleList,usedParts,usersList]=await Promise.all([
    api('/interventions'),api('/vehicles'),api(`/interventions/${invoice.intervention_id}/parts`),
    role==='ADMIN'?api('/users'):Promise.resolve([])
   ]);
   const intervention=interventionsList.find(i=>i.id===invoice.intervention_id);
   if(!intervention)throw new Error('Intervention associée introuvable ou inaccessible.');
   const vehicle=vehicleList.find(v=>v.id===intervention.vehicle_id);
   if(!vehicle)throw new Error('Véhicule associé introuvable ou inaccessible.');
   const customer=role==='ADMIN'?usersList.find(u=>u.id===vehicle.owner_id):user;
   const items=[
    {name:'Main-d’œuvre — '+intervention.description,qty:1,unit:Number(intervention.labor_cost||0)},
    ...usedParts.map(p=>({name:p.part_name||`Pièce #${p.part_id}`,qty:Number(p.quantity),unit:Number(p.unit_price)}))
   ];
   const calculated=items.reduce((sum,item)=>sum+item.qty*item.unit,0);
   const amount=Number(invoice.amount);
   const amountMismatch=Math.abs(calculated-amount)>0.015;
   const lines=items.map(item=>`<tr><td>${esc(item.name)}</td><td class="num">${esc(item.qty)}</td><td class="num">${esc(money(item.unit))}</td><td class="num">${esc(money(item.unit*item.qty))}</td></tr>`).join('');
   const date=invoice.issued_at?new Date(invoice.issued_at).toLocaleDateString('fr-TN'):'Non renseignée';
   const html=`<!doctype html><html lang="fr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Facture GaragePro n° ${esc(invoice.id)}</title><style>
    @page{size:A4;margin:15mm}*{box-sizing:border-box}body{font-family:Arial,Helvetica,sans-serif;color:#172337;margin:0;font-size:12px;line-height:1.55;background:#fff}
    header{display:flex;align-items:flex-start;justify-content:space-between;border-bottom:3px solid #f59a49;padding-bottom:20px;margin-bottom:26px}
    h1{color:#e7822f;font-size:26px;margin:0}h2{font-size:22px;margin:0;color:#14253b}h3{font-size:13px;color:#14253b;margin:0 0 8px}.muted{color:#617185}
    .block{margin:24px 0}.columns{display:flex;gap:24px}.columns>div{width:50%}.summary{background:#f4f6f9;padding:15px;border-radius:8px}
    table{width:100%;border-collapse:collapse;margin-top:12px}th{background:#172337;color:white;text-align:left;padding:11px}td{padding:11px;border-bottom:1px solid #dce2e9;vertical-align:top}.num{text-align:right;white-space:nowrap}
    .total{display:flex;justify-content:flex-end;margin-top:20px}.total span{padding:12px 16px;background:#fce7d5;border-radius:6px;font-weight:bold;font-size:17px}
    .note{margin-top:36px;padding-top:12px;border-top:1px solid #ddd;color:#64748b}.actions{margin-bottom:20px;display:flex;gap:10px}.actions button{padding:11px 18px;border:0;border-radius:7px;cursor:pointer;background:#f59a49;font-weight:bold}.warning{color:#b45309}
    @media print{.actions{display:none!important}header{break-after:avoid}tr{break-inside:avoid}}
   </style></head><body>
   <div class="actions"><button onclick="window.print()">Imprimer / Enregistrer en PDF</button><button onclick="window.close()">Fermer</button></div>
   <header><div><h1>GaragePro</h1><div class="muted">Gestion d'atelier automobile</div></div><div style="text-align:right"><h2>FACTURE</h2><strong>N° ${esc(invoice.id)}</strong><div>Date : ${esc(date)}</div><div>Statut : ${invoice.status==='PAID'?'PAYÉE':'NON PAYÉE'}</div></div></header>
   <div class="columns block"><div class="summary"><h3>GARAGE</h3><strong>GaragePro</strong><div class="muted">Coordonnées du garage à compléter avant remise au client</div></div>
   <div class="summary"><h3>CLIENT</h3><strong>${esc(customer?.name||'Client non renseigné')}</strong><div>${esc(customer?.email||'')}</div></div></div>
   <div class="block"><h3>VÉHICULE</h3><div>${esc(vehicle.brand)} ${esc(vehicle.model)} — ${esc(vehicle.plate)}</div>${vehicle.year?`<div>Année : ${esc(vehicle.year)}</div>`:''}<div>Intervention n° ${esc(intervention.id)}</div></div>
   <div class="block"><h3>DÉTAIL DE LA FACTURE</h3><table><thead><tr><th>Désignation</th><th class="num">Qté</th><th class="num">Prix unitaire</th><th class="num">Montant</th></tr></thead><tbody>${lines}</tbody></table>
   <div class="total"><span>Total enregistré : ${esc(money(invoice.amount))}</span></div>${amountMismatch?'<p class="warning">Attention : le total des lignes diffère du montant enregistré. Vérifiez la facture.</p>':''}
   <p class="muted">Montants affichés tels qu’enregistrés dans GaragePro. TVA non détaillée : à compléter selon le régime fiscal applicable.</p></div>
   <div class="note">Document généré depuis GaragePro. Compléter les mentions légales et fiscales du garage avant de remettre cette facture au client.</div>
   </body></html>`;
   popup.document.open();popup.document.write(html);popup.document.close();popup.focus();
  }catch(e){popup.close();setError('Impression impossible : '+e.message)}
 }
 // Filtrage instantané et universel de toutes les rubriques accessibles.
 // Les données proviennent de l'API protégée par les permissions du backend.
 const normalizeText = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
 const searchableRow = row => {
   const strings = Object.values(row).map(v => v === null ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v));
   if (row.vehicle_id != null) {
     const v = vehicles.find(x => Number(x.id) === Number(row.vehicle_id));
     if (v) strings.push(v.brand, v.model, v.plate);
   }
   if (row.mechanic_id != null) {
     const m = mechanics.find(x => Number(x.id) === Number(row.mechanic_id));
     if (m) strings.push(m.name, m.specialty);
   }
   if (row.owner_id != null) {
     const u = users.find(x => Number(x.id) === Number(row.owner_id));
     if (u) strings.push(u.name, u.email);
   }
   if (row.user_id != null) {
     const u = users.find(x => Number(x.id) === Number(row.user_id));
     if (u) strings.push(u.name, u.email);
   }
   if (row.intervention_id != null) {
     const intervention = invoiceInterventions.find(x => Number(x.id) === Number(row.intervention_id));
     const v = intervention && vehicles.find(x => Number(x.id) === Number(intervention.vehicle_id));
     if (v) {
       strings.push(v.brand, v.model, v.plate);
       const u = users.find(x => Number(x.id) === Number(v.owner_id));
       if (u) strings.push(u.name, u.email);
     }
     if (intervention) strings.push(intervention.description);
   }
   if (row.status) {
     const translations = { ...STATUSES, ...APPOINTMENT_STATUSES, UNPAID:'Non payée', PAID:'Payée' };
     strings.push(translations[row.status] || '');
   }
   return normalizeText(strings.join(' '));
 };
 const filteredRows = rows.filter(row => {
   const query = normalizeText(search.trim());
   if (query && !query.split(/\s+/).every(term => searchableRow(row).includes(term))) return false;
   if (statusFilter && row.status !== statusFilter) return false;
   if (dateFilter) {
     const date = page === 'appointments' ? row.starts_at :
                  page === 'invoices' ? row.issued_at :
                  page === 'audit' ? row.created_at : row.created_at;
     if (!date || !String(date).startsWith(dateFilter)) return false;
   }
   return true;
 });
 const statusOptions = page === 'interventions'
   ? [['REQUESTED','Demande'],['DIAGNOSIS','Diagnostic'],['REPAIR','Réparation'],['COMPLETED','Terminé'],['CANCELLED','Annulé']]
   : page === 'appointments' ? [['PENDING','En attente'],['PLANNED','Planifié'],['REJECTED','Refusé']]
   : page === 'invoices' ? [['UNPAID','Non payée'],['PAID','Payée']]
   : [];
 const resetFilters = () => {setSearch('');setStatusFilter('');setDateFilter('')};
 const title=page==='dashboard'?(role==='MECANICIEN'?'Mon espace mécanicien':'Tableau de bord'):DEFINITIONS[page]?.title
 const canCreate=role==='ADMIN'||(role==='CLIENT'&&['vehicles','appointments'].includes(page))
 const canEdit=page!=='users'&&((['vehicles','appointments'].includes(page)&&role==='CLIENT')||role==='ADMIN')
 const canDelete=canEdit&&['vehicles','mechanics','parts','appointments','interventions'].includes(page)
 if(!token||!user)return <div className="login-shell"><div className="login-aside"><div className="mark"><Wrench size={27}/><b>GaragePro</b></div><div className="login-hero"><span className="eyebrow">GESTION D’ATELIER</span><h1>Votre garage,<br/><em>plus intelligent.</em></h1><p>Suivez les interventions, les rendez-vous et les stocks depuis un seul espace professionnel.</p><div className="hero-chip"><CheckCircle2 size={16}/> Une plateforme, trois espaces métier.</div></div><div className="login-bottom">Gestion automobile • FastAPI + React</div></div><div className="login-side"><form onSubmit={auth} className="login-card"><div className="mobile-brand">🔧 GaragePro</div><h2>{authMode==='login'?'Connexion':'Créer un compte'}</h2><p>{authMode==='login'?'Accédez à votre tableau de bord.':'Inscription réservée aux clients.'}</p>{error&&<div className="error">{error}</div>}{notice&&<div className="success">{notice}</div>}{authMode==='register'&&<label>Nom complet<input required value={credentials.name||''} onChange={e=>setCredentials({...credentials,name:e.target.value})}/></label>}<label>Adresse e-mail<input type="email" required value={credentials.email||''} onChange={e=>setCredentials({...credentials,email:e.target.value})}/></label><label>Mot de passe<input type="password" minLength={authMode==='register'?8:undefined} required value={credentials.password||''} onChange={e=>setCredentials({...credentials,password:e.target.value})}/></label><button className="primary full" disabled={loading}>{authMode==='login'?'Se connecter':'Créer mon compte'} <ChevronRight size={17}/></button><button type="button" className="link-button" onClick={()=>{setError('');setNotice('');setAuthMode(authMode==='login'?'register':'login')}}>{authMode==='login'?'Nouveau client ? Créer un compte':'Déjà inscrit ? Se connecter'}</button></form></div></div>
 return <div className="layout"><aside className={`sidebar ${sidebar?'open':''}`}><div className="brand"><span className="brand-icon"><Wrench size={22}/></span><span>Garage<span className="brand-accent">Pro</span><small>WORKSHOP OS</small></span></div><div className="nav-label">ESPACE DE TRAVAIL</div><nav>{available.map(([id,label,Icon])=><button key={id} className={`navitem ${page===id?'active':''}`} onClick={()=>{setPage(id);resetFilters();setSidebar(false);setModal(null)}}><Icon size={18}/>{label}{page===id&&<span className="nav-dot"/>}</button>)}</nav><div className="sidebar-foot"><span className="online-dot"/> Système opérationnel <small>GaragePro v1.0</small></div></aside><main className="workspace"><header className="topbar"><button className="hamburger" onClick={()=>setSidebar(!sidebar)}><Menu/></button><span className="crumb">Espace de travail <ChevronRight size={15}/> <strong>{title}</strong></span><div className="user-menu"><span className="avatar">{(user.name||'U').slice(0,1).toUpperCase()}</span><span className="user-info"><b>{user.name}</b><small>{role}</small></span><button className="icon-button" title="Déconnexion" onClick={logout}><LogOut size={18}/></button></div></header><div className="page-content"><div className="page-heading"><div><div className="eyebrow dark">GARAGEPRO / {title?.toUpperCase()}</div><h1>{title}</h1><p>{page==='dashboard'?'Une vision claire sur l’activité de votre garage.':page==='appointments'&&role==='CLIENT'?'Créez, modifiez et supprimez vos demandes en attente. Après acceptation, le statut devient « Planifié » automatiquement.':page==='vehicles'&&role==='MECANICIEN'?'Consultez les véhicules ajoutés par l’administrateur et les véhicules clients dont vous avez accepté le rendez-vous.':'Gérez vos données métier en toute simplicité.'}</p></div><button className="outline" onClick={load} disabled={loading}><RefreshCw size={16}/> Actualiser</button></div>{error&&<div className="error sticky"><CircleAlert size={17}/>{error}<button onClick={()=>setError('')}>×</button></div>}{notice&&<div className="success sticky"><CheckCircle2 size={17}/>{notice}<button onClick={()=>setNotice('')}>×</button></div>}
 {page==='dashboard'?<>{role==='ADMIN'&&Array.isArray(dashboard.stock_alerts)&&dashboard.stock_alerts.length>0&&<section role="alert" style={{background:'#fff7ed',border:'1px solid #fdba74',borderRadius:14,padding:'16px 20px',marginBottom:18,color:'#7c2d12'}}><div style={{display:'flex',alignItems:'center',gap:9,fontWeight:800,marginBottom:8}}><CircleAlert size={20}/> Alerte stock — réapprovisionnement nécessaire</div><p style={{margin:'0 0 10px',fontSize:13}}>{dashboard.parts_out_of_stock||0} référence(s) en rupture · {dashboard.parts_low_stock||0} référence(s) en stock faible (1 à 5 unités)</p><div style={{display:'flex',flexWrap:'wrap',gap:8}}>{dashboard.stock_alerts.map(p=><span key={p.id} style={{padding:'6px 10px',borderRadius:8,background:p.stock===0?'#fee2e2':'#ffedd5',color:p.stock===0?'#991b1b':'#9a3412',fontSize:13,fontWeight:600}}>{p.sku} — {p.name} : {p.stock} restante(s) {p.stock===0?'(RUPTURE)':'(FAIBLE)'}</span>)}</div><button className="outline" style={{marginTop:12}} onClick={()=>setPage('parts')}>Consulter le stock</button></section>}{role==='ADMIN'&&Array.isArray(dashboard.stock_alerts)&&dashboard.stock_alerts.length===0&&<p style={{color:'#15803d',fontSize:13,marginBottom:14}}>✓ Aucune alerte de stock : toutes les références ont plus de 5 unités.</p>}<div className="stats-grid">{Object.entries(dashboard).filter(([_,v])=>typeof v!=='object').map(([k,v],i)=><div className="stat-card" key={k}><div className="stat-icon">{i%3===0?<CarFront size={21}/>:i%3===1?<Wrench size={21}/>:<CheckCircle2 size={21}/>}</div><div className="stat-name">{{vehicles:'Véhicules',clients:'Clients',interventions:'Interventions',requested:'Demandes',in_repair:'En réparation',completed:'Terminées',parts_low_stock:'Stock faible (1–5)',parts_out_of_stock:'En rupture',revenue:'Revenus (TND)'}[k]||k}</div><div className="stat-number">{v}</div></div>)}</div>{role==='MECANICIEN'&&<div className="dashboard-panel"><div className="panel-title"><div><h3>Mes missions affectées</h3><p>Accédez directement à vos interventions et mettez à jour leur statut.</p></div><Wrench size={22}/></div>{myTasks.length===0?<p className="muted">Aucune intervention ne vous est actuellement affectée. L'administrateur doit vous choisir comme mécanicien lors de la création.</p>:<div className="table-scroll"><table><thead><tr><th>N°</th><th>Travail demandé</th><th>État</th><th>Action</th></tr></thead><tbody>{myTasks.map(item=><tr key={item.id}><td>{item.id}</td><td>{item.description}</td><td>{STATUSES[item.status]||item.status}</td><td><button className="text-action" onClick={()=>{setPage('interventions');setSearch('')}}>Ouvrir mes interventions</button></td></tr>)}</tbody></table></div>}</div>}<div className="dashboard-panel"><div className="panel-title"><div><h3>Suivi des interventions</h3><p>Répartition par état actuel</p></div><ClipboardList size={22}/></div><div className="status-summary">{Object.entries(dashboard.by_status||{}).map(([k,v])=><div className="status-line" key={k}><span>{STATUSES[k]}</span><div className="status-track"><span style={{width:`${dashboard.interventions?Math.round(100*v/dashboard.interventions):0}%`}}/></div><b>{v}</b></div>)}</div>{!dashboard.by_status&&<p className="muted">Consultez vos interventions depuis le menu.</p>}</div></>:<><div className="toolbar"><div className="searchbox"><Search size={17}/><input aria-label="Rechercher" placeholder="Rechercher par nom, référence, véhicule, statut..." value={search} onChange={e=>setSearch(e.target.value)}/></div>{statusOptions.length>0&&<select aria-label="Filtrer par statut" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="">Tous les statuts</option>{statusOptions.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>}{['appointments','interventions','invoices','audit'].includes(page)&&<input aria-label="Filtrer par date" type="date" value={dateFilter} onChange={e=>setDateFilter(e.target.value)}/>}<button type="button" className="outline" onClick={resetFilters}>Effacer les filtres</button>{canCreate&&!!DEFINITIONS[page]?.fields.length&&<button className="primary" onClick={()=>startForm()}><Plus size={17}/> Ajouter</button>}</div><div className="table-card"><div className="table-top"><h3>{DEFINITIONS[page]?.title}</h3><span>{filteredRows.length} résultat(s) / {rows.length} élément(s)</span></div><div className="table-scroll"><table><thead><tr>{DEFINITIONS[page]?.headers.map(([k,title])=><th key={k}>{title}</th>)}<th>Actions</th></tr></thead><tbody>{filteredRows.length===0?<tr><td colSpan={(DEFINITIONS[page]?.headers.length||0)+1} className="empty">{loading?'Chargement...':'Aucun résultat. Modifie ou efface les filtres.'}</td></tr>:filteredRows.map(row=><tr key={row.id}>{DEFINITIONS[page].headers.map(([k])=><td key={k}>{k==='photo'? (vehiclePhotos[row.id]?<img className="vehicle-thumb" src={vehiclePhotos[row.id]} alt={`Photo ${row.brand} ${row.model}`} />:<span className="no-vehicle-photo">Aucune photo</span>):k==='stock'&&page==='parts'?<span style={{fontWeight:700,color:Number(row[k])===0?'#b91c1c':Number(row[k])<=5?'#c2410c':'#15803d'}}>{row[k]} {Number(row[k])===0?'— Rupture':Number(row[k])<=5?'— Faible':'— Normal'}</span>:k==='status'?<span className={`pill ${row[k]?.toLowerCase()}`}>{(page==='appointments'?APPOINTMENT_STATUSES:STATUSES)[row[k]]||row[k]}</span>:k==='active'?(row[k]?'Oui':'Non'):k==='vehicle_id'&&['appointments','interventions'].includes(page)?(vehicles.find(v=>v.id===row[k])?`${vehicles.find(v=>v.id===row[k]).brand} ${vehicles.find(v=>v.id===row[k]).model} — ${vehicles.find(v=>v.id===row[k]).plate}`:`Véhicule #${row[k]}`):k==='mechanic_id'&&page==='appointments'?(row[k]?(mechanics.find(m=>m.id===row[k])?.name||`Mécanicien #${row[k]}`):'Non affecté'):String(row[k]??'—').slice(0,85)}</td>)}<td><div className="actions">{canEdit&&(page!=='appointments'||row.status==='PENDING')&&DEFINITIONS[page].fields.length>0&&<button title="Modifier" onClick={()=>startForm(row)}><Pencil size={16}/></button>}{canDelete&&(page!=='appointments'||['PENDING','REJECTED'].includes(row.status))&&<button title="Supprimer" onClick={()=>remove(row.id)}><Trash2 size={16}/></button>}{page==='appointments'&&role==='MECANICIEN'&&row.status==='PENDING'&&<button className="text-action" disabled={loading} title="Confirmer ce rendez-vous" onClick={()=>action(()=>api(`/appointments/${row.id}/accept`,{method:'PATCH'}))}>Accepter</button>}{page==='interventions'&&role!=='CLIENT'&&NEXT[row.status]?.length>0&&<button className="text-action" onClick={()=>{setExtra({kind:'transition',item:row,status:NEXT[row.status][0],diagnosis:row.diagnosis||''});setModal({type:'extra'})}}>{role==='MECANICIEN'?'Avancer le travail':'Statut'}</button>}{page==='interventions'&&role!=='CLIENT'&&row.status==='REPAIR'&&<button className="text-action" onClick={()=>{setExtra({kind:'parts',item:row,items:[{part_id:'',quantity:1}]});setModal({type:'extra'})}}>+ Pièce</button>}{page==='interventions'&&role==='MECANICIEN'&&['DIAGNOSIS','REPAIR','COMPLETED'].includes(row.status)&&<button className="text-action" onClick={()=>openReport(row)}>Compte rendu</button>}{page==='interventions'&&role==='ADMIN'&&row.status==='COMPLETED'&&<button className="text-action" onClick={()=>action(()=>api(`/invoices/${row.id}`,{method:'POST'}))}>Facturer</button>}{page==='invoices'&&['ADMIN','CLIENT'].includes(role)&&<button className="text-action" title="Imprimer la facture ou enregistrer en PDF" onClick={()=>printInvoice(row)}>Imprimer</button>}{page==='invoices'&&role==='ADMIN'&&row.status==='UNPAID'&&<button className="text-action" onClick={()=>action(()=>api(`/invoices/${row.id}`,{method:'PATCH',body:JSON.stringify({status:'PAID'})}))}>Marquer payée</button>}</div></td></tr>)}</tbody></table></div></div></>}
 </div></main>{modal&&<div className="modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setModal(null)}}><div className="modal"><div className="modal-head"><h2>{modal.type==='new'?'Nouvel enregistrement':modal.type==='edit'?'Modifier':'Action métier'}</h2><button onClick={()=>{setModal(null);setError('')}}>×</button></div>{modal.type==='extra'?<form onSubmit={e=>{e.preventDefault();if(extra.kind==='report'){saveReport(e);return}if(extra.kind==='parts'){
  const items=extra.items.map(p=>({part_id:Number(p.part_id),quantity:Number(p.quantity)}));
  if(items.some(p=>!p.part_id||!Number.isInteger(p.quantity)||p.quantity<1)){setError('Sélectionnez une pièce et une quantité valide pour chaque ligne.');return}
  if(new Set(items.map(p=>p.part_id)).size!==items.length){setError('Une pièce ne peut être sélectionnée qu’une fois.');return}
  action(()=>api(`/interventions/${extra.item.id}/parts/bulk`,{method:'POST',body:JSON.stringify({items})}));return;
}const data={status:extra.status,diagnosis:extra.diagnosis||null};action(()=>api(`/interventions/${extra.item.id}/status`,{method:'PATCH',body:JSON.stringify(data)}))}}>{extra.kind==='report'?<><p className="muted">Intervention n° {extra.item.id} — Compte rendu des travaux réalisés</p><label>Travaux effectués<textarea required minLength={5} value={reportText} onChange={e=>setReportText(e.target.value)} placeholder="Décrivez votre travail, les contrôles effectués et les résultats"/></label><label>Observations<textarea value={reportNotes} onChange={e=>setReportNotes(e.target.value)} placeholder="Ex. : Véhicule prêt, conseil au client, anomalie supplémentaire"/></label></>:extra.kind==='transition'?<><label>Nouvel état<select value={extra.status} onChange={e=>setExtra({...extra,status:e.target.value})}>{NEXT[extra.item.status].map(x=><option key={x} value={x}>{STATUSES[x]}</option>)}</select></label>{extra.item.status==='DIAGNOSIS'&&<label>Diagnostic obligatoire<textarea value={extra.diagnosis} onChange={e=>setExtra({...extra,diagnosis:e.target.value})}/></label>}</>:<><p className="muted">Sélectionnez plusieurs pièces et indiquez la quantité de chacune. Tout sera enregistré en une seule opération.</p>{extra.items.map((entry,index)=><div className="multi-part-row" key={index}><label>Pièce détachée {index+1}<select required value={entry.part_id} onChange={e=>setExtra(prev=>({...prev,items:prev.items.map((p,i)=>i===index?{...p,part_id:e.target.value}:p)}))}><option value="">Choisir une pièce</option>{parts.map(part=><option key={part.id} value={part.id} disabled={part.stock<=0||(extra.items.some((p,i)=>i!==index&&String(p.part_id)===String(part.id)))}>{part.name} — {part.sku} (Stock : {part.stock}, Prix : {part.unit_price} TND)</option>)}</select></label><label>Quantité<input type="number" required min="1" max={parts.find(p=>String(p.id)===String(entry.part_id))?.stock||undefined} value={entry.quantity} onChange={e=>setExtra(prev=>({...prev,items:prev.items.map((p,i)=>i===index?{...p,quantity:e.target.value}:p)}))}/></label>{extra.items.length>1&&<button type="button" className="outline" onClick={()=>setExtra(prev=>({...prev,items:prev.items.filter((_,i)=>i!==index)}))}>Retirer cette pièce</button>}</div>)}{parts.length===0&&<p className="muted">Aucune pièce disponible. Ajoutez d’abord des pièces dans « Pièces & stock ».</p>}<button type="button" className="outline" disabled={extra.items.length>=Math.min(parts.length,50)} onClick={()=>setExtra(prev=>({...prev,items:[...prev.items,{part_id:'',quantity:1}]}))}><Plus size={15}/> Ajouter une autre pièce</button></>}{error&&<div className="error">{error}</div>}<div className="modal-actions"><button type="button" className="outline" onClick={()=>setModal(null)}>Annuler</button><button className="primary" disabled={loading||reportLoading}>{extra.kind==='report'?'Enregistrer mon compte rendu':'Valider'}</button></div></form>:<form onSubmit={submit}>{DEFINITIONS[page].fields.filter(([k])=>!(k==='owner_id'&&role==='CLIENT')).map(([k,label,type])=><label key={k}>{label}{k==='owner_id'&&role==='ADMIN'&&users.length>0?<select value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})} required><option value="">Choisir un client</option>{users.filter(u=>u.role==='CLIENT').map(u=><option value={u.id} key={u.id}>{u.name} (#{u.id})</option>)}</select>:k==='user_id'&&page==='mechanics'?<select required value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})}><option value="">Choisir un utilisateur mécanicien</option>{users.filter(u=>u.role==='MECANICIEN').map(u=><option key={u.id} value={u.id}>{u.name} — {u.email} (#{u.id})</option>)}</select>:k==='role'&&page==='users'?<select required value={values[k]||'CLIENT'} onChange={e=>setValues({...values,[k]:e.target.value})}><option value="CLIENT">Client</option><option value="MECANICIEN">Mécanicien</option><option value="ADMIN">Administrateur</option></select>:k==='vehicle_id'&&['appointments','interventions'].includes(page)?<select required value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value,appointment_id:''})}><option value="">Choisir un véhicule</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.brand} {v.model} — {v.plate} (#{v.id})</option>)}</select>:k==='appointment_id'&&page==='interventions'?<select value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})}><option value="">Sans rendez-vous</option>{appointments.filter(a=>String(a.vehicle_id)===String(values.vehicle_id)&&(!rows.some(i=>i.appointment_id===a.id&&i.id!==modal?.id))).map(a=><option key={a.id} value={a.id}>{`RDV #${a.id} — ${new Date(a.starts_at).toLocaleString('fr-FR')} — ${a.reason}`}</option>)}</select>:k==='mechanic_id'&&['appointments','interventions'].includes(page)?<select value={values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})}><option value="">Sans mécanicien</option>{mechanics.map(m=><option key={m.id} value={m.id}>{m.name} — {m.specialty} (#{m.id})</option>)}</select>:<input type={type==='datetime-local'?'datetime-local':type} step={type==='number'?'any':undefined} min={['stock','unit_price','labor_cost'].includes(k)?0:undefined} minLength={k==='password'?8:undefined} autoComplete={k==='password'?'new-password':undefined} required={!['owner_id','year','mechanic_id','appointment_id'].includes(k)} value={type==='datetime-local'&&values[k]?String(values[k]).slice(0,16):values[k]??''} onChange={e=>setValues({...values,[k]:e.target.value})}/>}</label>)}{page==='vehicles'&&<label>Photo du véhicule (JPG, PNG ou WEBP — compression automatique)
   <input type="file" accept="image/jpeg,image/png,image/webp" onChange={selectVehicleImage} disabled={photoProcessing}/>{photoProcessing&&<span className="muted">Compression de la photo en cours…</span>}
   {(selectedVehiclePhoto||(modal.type==='edit'&&vehiclePhotos[modal.id]))&&<img className="vehicle-preview" src={selectedVehiclePhoto||vehiclePhotos[modal.id]} alt="Aperçu du véhicule"/>}
   {modal.type==='edit'&&vehiclePhotos[modal.id]&&<button type="button" className="outline" onClick={async()=>{
     if(!confirm('Supprimer la photo de ce véhicule ?'))return
     try{await api(`/vehicles/${modal.id}/photo`,{method:'DELETE'});setSelectedVehiclePhoto(null);setVehiclePhotos(old=>({...old,[modal.id]:null}));flash('Photo supprimée')}
     catch(e){setError(e.message)}
   }}>Supprimer la photo existante</button>}
 </label>}{error&&<div className="error">{error}</div>}<div className="modal-actions"><button type="button" className="outline" onClick={()=>setModal(null)}>Annuler</button><button className="primary" disabled={loading||photoProcessing}>{photoProcessing?"Compression…":"Enregistrer"}</button></div></form>}</div></div>}</div>
}
createRoot(document.getElementById('root')).render(<App/>)
