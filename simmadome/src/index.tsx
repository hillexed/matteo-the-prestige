import React from 'react';
import ReactDOM from 'react-dom';
import { BrowserRouter as Router, Switch, Route, Link } from 'react-router-dom';
import './index.css';
import GamesPage from './GamesPage';
import GamePage from './GamePage';
import CreateLeague from './CreateLeague';
import discordlogo from "./img/discord.png";
import reportWebVitals from './reportWebVitals';
import patreonLogo from './img/patreon.png';
import githubLogo from './img/github.png';
import twitterLogo from './img/twitter.png';

ReactDOM.render(
  <React.StrictMode>
    <Router>
      <Header />
      <Switch>
        <Route path="/game/:id" component={GamePage}/>
        <Route path="/create_league" component={CreateLeague} />
        <Route path="/" component={GamesPage}/>
      </Switch>
    </Router>
  </React.StrictMode>,
  document.getElementById('root')
);


function Header() {
  return (
    <div id="header">
      <div id="links">
        <div id="nav_links">
          <Link to="/create_league">Create a League</Link>
        </div>
        <div id="link_div">
          <a href="https://github.com/hillexed/matteo-the-prestige" className="github_link" target="_blank" rel="noopener noreferrer">
            <img className="github_logo" src={githubLogo} alt="Github"/>
          </a>
        </div>
      </div>
      <a href="/" className="page_header"><h2 className="page_header" style={{fontSize:"50px"} as React.CSSProperties}>THE TWINNADOME</h2></a>
      <h2 className="page_header">Join SIBR on <a href="https://discord.gg/UhAajY2NCW" className="link"><img src={discordlogo} alt="" height="30"/></a> to start your own games!</h2>
    </div>
  );
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
