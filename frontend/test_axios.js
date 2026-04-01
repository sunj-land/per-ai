import axios from 'axios';
console.log(axios.getUri({baseURL: '/api', url: '/v1/plans'}));
console.log(axios.getUri({baseURL: '/api', url: 'v1/plans'}));
