import App from './App.svelte';


const API = "http://localhost:5000";
const app = new App({
	target: document.body,
	props: {
		api: API
	}
});

export default app;