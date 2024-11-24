import App from './App.svelte';


const API = "http://localhost:3004";
const app = new App({
	target: document.body,
	props: {
		api: API
	}
});

export default app;