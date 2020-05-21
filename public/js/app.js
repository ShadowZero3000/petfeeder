const router=new VueRouter({
  routes:[
    {path:'/',name:'home',component: Vue.component('meals')},
    {path:'/meals',name:'meals',component: Vue.component('meals'),},
    {path:'/healthchecks',name:'healthchecks',component: Vue.component('healthchecks'),},
    {path:'/settings',name:'settings',component: Vue.component('settings'),}
  ]
})

var vm = new Vue({
  router,
  el: '#vuewrapper',
  methods: {
    take_photo() {
      axios
        .post('//'+window.location.host+'/api/photo', {})
        .then(response => {
          me = this
        })
    }
  }
})
