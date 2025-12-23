import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Eye, XCircle, ChefHat, CodeXml, BarChart3, RefreshCw, Loader2, Download } from 'lucide-react';
import './App.css';

const ReportPage = () => {
  const { id } = useParams();

  // --- 1. DEFINE THE API URL
  const API_BASE_URL = import.meta.env.VITE_API_URL;

  // --- 2. STATE VARIABLES ---
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [refreshJobId, setRefreshJobId] = useState(null);
  const [refreshText, setRefreshText] = useState("");

  // --- 3. EFFECTS ---

  // Effect A: Fetch the Report initially
  useEffect(() => {
    const fetchReport = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/view-report/${id}`);
          if (!response.ok) throw new Error("Report not found");
          const data = await response.json();
          
          // Sort by Score (High to Low)
          const sortedData = data.data.sort((a, b) => (b.Score || 0) - (a.Score || 0));
          data.data = sortedData.map((item, index) => ({ ...item, rank: index + 1 }));
          
          setReport(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
    };
    fetchReport();
  }, [id, API_BASE_URL]);

  // Effect B: Poll for Refresh Progress
  useEffect(() => {
    let interval;
    if (refreshJobId && refreshing) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE_URL}/progress/${refreshJobId}`);
          const data = res.data;

          if (data.status === "processing" || data.status === "queued") {
            const current = data.current;
            const total = data.total;
            if (total > 0) {
              const pct = Math.round((current / total) * 100);
              setRefreshProgress(pct);
              setRefreshText(`Checking ${current} / ${total}...`);
            }
          } else if (data.status === "completed") {
            clearInterval(interval);
            setRefreshing(false);
            setRefreshJobId(null);
            alert("Report Updated Successfully!");
            window.location.reload(); 
          } else if (data.status === "failed") {
            alert("Refresh Failed: " + data.error);
            setRefreshing(false);
            clearInterval(interval);
          }
        } catch (err) {
          console.error("Polling error", err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [refreshJobId, refreshing, API_BASE_URL]);


  // --- 4. HELPER FUNCTIONS ---
  const getValue = (obj, targetKey) => {
    if (!obj) return "";
    const key = Object.keys(obj).find(k => k.toLowerCase() === targetKey.toLowerCase());
    return key ? obj[key] : ""; 
  };

  const getPlatformStats = (student, prefix) => {
    const keys = Object.keys(student).filter(k => k.startsWith(prefix));
    const total = keys.length;
    const solved = keys.filter(k => student[k] === "Solved").length;
    return { solved, total, keys };
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setRefreshProgress(0);
    setRefreshText("Starting refresh...");
    
    try {
      const response = await axios.post(`${API_BASE_URL}/refresh-report/${id}`);
      setRefreshJobId(response.data.job_id);
    } catch (err) {
      alert("Failed to start refresh");
      setRefreshing(false);
    }
  };

  const handleDownload = () => {
    window.open(`${API_BASE_URL}/download-report/${id}`, '_blank');
  };

  // --- 5. RENDER ---
  if (loading) return <div className="container text-center"><h3>Loading Report...</h3></div>;
  if (error) return <div className="container text-center" style={{color:'red'}}><h3>Error: {error}</h3></div>;

  return (
    <div className="container" style={{ maxWidth: '1200px' }}>
      <h1>Student Report Card</h1>
      
      <div className="card">
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
            
            {/* Title & Timestamp */}
            <div>
               <h3>Report Summary</h3>
               {report.last_updated && (
                  <span style={{fontSize:'0.8rem', color:'#666'}}>
                    Last Updated: {new Date(report.last_updated).toLocaleString()}
                  </span>
               )}
            </div>

            {/* Buttons */}
            <div style={{display:'flex', alignItems:'center', gap:'15px'}}>
                
                {refreshing && (
                  <div style={{textAlign:'right'}}>
                      <span style={{fontSize:'0.9rem', fontWeight:'bold', color:'#007bff'}}>
                        {refreshText} ({refreshProgress}%)
                      </span>
                      <div style={{width:'150px', height:'4px', background:'#eee', borderRadius:'2px', marginTop:'4px'}}>
                          <div style={{width:`${refreshProgress}%`, height:'100%', background:'#007bff', transition:'width 0.3s'}}></div>
                      </div>
                  </div>
                )}

                {/* DOWNLOAD BUTTON */}
                <button 
                  onClick={handleDownload}
                  className="view-btn"
                  style={{
                    backgroundColor: '#007bff', 
                    display:'flex', alignItems:'center', gap:'8px',
                    marginRight: '10px'
                  }}
                >
                  <Download size={18}/> Download Excel
                </button>

                {/* REFRESH BUTTON */}
                <button 
                  onClick={handleRefresh} 
                  disabled={refreshing}
                  className="view-btn"
                  style={{
                    backgroundColor: refreshing ? '#ccc' : '#28a745',
                    display:'flex', alignItems:'center', gap:'8px',
                    cursor: refreshing ? 'not-allowed' : 'pointer'
                  }}
                >
                  {refreshing ? <Loader2 className="spin" size={18}/> : <RefreshCw size={18}/>}
                  {refreshing ? "Updating..." : "Refresh Data"}
                </button>

                <span style={{fontWeight:'bold', color:'#007bff', fontSize:'1.1rem', borderLeft:'2px solid #eee', paddingLeft:'15px'}}>
                    Total: {report.total_students}
                </span>
            </div>
        </div>
        
        {/* TABLE */}
        <div style={{overflowX: 'auto'}}>
            <table className="report-table">
                <thead>
                    <tr>
                        <th style={{width: '50px'}}>Rank</th>
                        <th>Roll No</th>
                        <th>Name</th>
                        <th style={{textAlign:'center'}}>Profiles</th>
                        <th style={{textAlign:'center'}}>Score</th>
                        <th style={{textAlign:'center', color:'#ffa116'}}>LeetCode</th>
                        <th style={{textAlign:'center', color:'#5d4037'}}>CodeChef</th>
                        <th style={{textAlign:'center', color:'#007bff'}}>CodeForces</th>
                        <th style={{textAlign:'center'}}>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {report.data.map((student) => {
                        const studentName = getValue(student, "name") || "Unknown";
                        const rollNumber = getValue(student, "roll number") || getValue(student, "roll-number") || "-";
                        
                        const cfLink = getValue(student, "codeforces");
                        const lcLink = getValue(student, "leetcode");
                        const ccLink = getValue(student, "codechef");

                        const cfStats = getPlatformStats(student, "CF:");
                        const lcStats = getPlatformStats(student, "LC:");
                        const ccStats = getPlatformStats(student, "CC:");
                        const totalQs = cfStats.total + lcStats.total + ccStats.total;

                        return (
                          <tr key={student.rank}>
                              <td style={{fontWeight:'bold', color:'#888'}}>#{student.rank}</td>
                              <td style={{fontFamily:'monospace', color:'#555'}}>{rollNumber}</td>
                              <td style={{fontWeight:'600'}}>{studentName}</td>
                              <td style={{textAlign:'center'}}>
                                  <div style={{display:'flex', gap:'12px', justifyContent:'center'}}>
                                      {lcLink ? (
                                        <a href={`https://leetcode.com/${lcLink}`} target="_blank" title="LeetCode Profile">
                                            <CodeXml size={20} color="#ffa116" strokeWidth={2.5}/>
                                        </a>
                                      ) : <span style={{opacity:0.2}}><CodeXml size={20}/></span>}

                                      {ccLink ? (
                                        <a href={`https://www.codechef.com/users/${ccLink}`} target="_blank" title="CodeChef Profile">
                                            <ChefHat size={20} color="#5d4037" strokeWidth={2.5}/>
                                        </a>
                                      ) : <span style={{opacity:0.2}}><ChefHat size={20}/></span>}

                                      {cfLink ? (
                                        <a href={`https://codeforces.com/profile/${cfLink}`} target="_blank" title="Codeforces Profile">
                                            <BarChart3 size={20} color="#007bff" strokeWidth={2.5}/>
                                        </a>
                                      ) : <span style={{opacity:0.2}}><BarChart3 size={20}/></span>}
                                  </div>
                              </td>

                              <td style={{textAlign:'center'}}>
                                  <span className={`badge ${student.Score === totalQs ? 'green' : student.Score > 0 ? 'yellow' : 'red'}`} style={{fontSize:'0.9rem'}}>
                                      {student.Score} / {totalQs}
                                  </span>
                              </td>

                              <td style={{textAlign:'center', fontSize:'0.9rem'}}>
                                  {lcStats.total > 0 ? 
                                    <span style={{color: lcStats.solved === lcStats.total ? '#15803d' : '#444'}}>
                                        <b>{lcStats.solved}</b> / {lcStats.total}
                                    </span> 
                                  : <span style={{color:'#ccc'}}>-</span>}
                              </td>

                              <td style={{textAlign:'center', fontSize:'0.9rem'}}>
                                  {ccStats.total > 0 ? 
                                    <span style={{color: ccStats.solved === ccStats.total ? '#15803d' : '#444'}}>
                                        <b>{ccStats.solved}</b> / {ccStats.total}
                                    </span> 
                                  : <span style={{color:'#ccc'}}>-</span>}
                              </td>

                              <td style={{textAlign:'center', fontSize:'0.9rem'}}>
                                  {cfStats.total > 0 ? 
                                    <span style={{color: cfStats.solved === cfStats.total ? '#15803d' : '#444'}}>
                                        <b>{cfStats.solved}</b> / {cfStats.total}
                                    </span> 
                                  : <span style={{color:'#ccc'}}>-</span>}
                              </td>

                              <td style={{textAlign:'center'}}>
                                  <button 
                                    onClick={() => setSelectedStudent(student)}
                                    className="view-btn-small"
                                  >
                                      <Eye size={16} style={{marginRight:'4px'}}/> View
                                  </button>
                              </td>
                          </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
      </div>

      {selectedStudent && (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(2px)',
            display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div style={{
              background: 'white', padding: '24px', borderRadius: '16px', width: '90%', maxWidth: '500px', 
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
          }}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px', borderBottom:'1px solid #eee', paddingBottom:'10px'}}>
                <div>
                    <h2 style={{margin:0, fontSize:'1.5rem'}}>{getValue(selectedStudent, "name")}</h2>
                    <p style={{margin:0, color:'#666', fontSize:'0.9rem'}}>{getValue(selectedStudent, "roll number") || getValue(selectedStudent, "roll-number")}</p>
                </div>
                <button onClick={() => setSelectedStudent(null)} style={{background:'none', border:'none', cursor:'pointer', color:'#999', padding:'4px'}}>
                    <XCircle size={28} />
                </button>
            </div>
            
            <div style={{maxHeight:'60vh', overflowY:'auto'}}>
                {['CF', 'LC', 'CC'].map(platform => {
                   const stats = getPlatformStats(selectedStudent, `${platform}:`);
                   if (stats.total === 0) return null;
                   
                   const color = platform === 'LC' ? '#ffa116' : platform === 'CC' ? '#5d4037' : '#007bff';
                   const icon = platform === 'LC' ? <CodeXml size={18}/> : platform === 'CC' ? <ChefHat size={18}/> : <BarChart3 size={18}/>;
                   const name = platform === 'LC' ? 'LeetCode' : platform === 'CC' ? 'CodeChef' : 'CodeForces';

                   return (
                       <div key={platform} style={{marginBottom:'20px'}}>
                           <div style={{display:'flex', alignItems:'center', gap:'8px', marginBottom:'10px', color: color, fontWeight:'bold'}}>
                                {icon} {name}
                                <span style={{marginLeft:'auto', background:'#f3f4f6', padding:'2px 8px', borderRadius:'10px', fontSize:'0.8rem', color:'#333'}}>
                                    {stats.solved}/{stats.total} Solved
                                </span>
                           </div>
                           {stats.keys.map(key => (
                               <div key={key} style={{
                                   display:'flex', justifyContent:'space-between', fontSize:'0.9rem', marginBottom:'6px', padding:'8px', 
                                   background: selectedStudent[key] === "Solved" ? '#f0fdf4' : '#fef2f2',
                                   borderRadius:'6px', border: selectedStudent[key] === "Solved" ? '1px solid #dcfce7' : '1px solid #fee2e2'
                               }}>
                                   <span style={{fontFamily:'monospace'}}>{key.split(': ')[1]}</span>
                                   <span style={{
                                       color: selectedStudent[key] === "Solved" ? '#166534' : '#991b1b',
                                       fontWeight: 'bold', fontSize:'0.85rem', display:'flex', alignItems:'center', gap:'4px'
                                   }}>
                                       {selectedStudent[key]}
                                   </span>
                               </div>
                           ))}
                       </div>
                   )
                })}
            </div>
            
            <button onClick={() => setSelectedStudent(null)} style={{
                width:'100%', padding:'12px', backgroundColor:'#1a1a1a', color:'white', border:'none', borderRadius:'8px', cursor:'pointer', fontWeight:'bold', marginTop:'10px'
            }}>Close Details</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportPage;
