function parseFailure(error) {
  vm.showModal(error.response.data)
}

var vm = new Vue({
  el: '#vuewrapper',
  data () {
    return {
      errorMessage: null,
      events: {}
    }
  },
  computed: {
    eventsByType: function() {
      return _.groupBy(this.events, (item) => item.type);
    }
  },
  mounted () {
    this.refreshData()
  },
  methods: {
    feed() {
      axios
        .get('//'+window.location.host+'/api/feed')
        .then(response => {
          me = this
        })
    },
    refreshData() {
      axios
        .get('//'+window.location.host+'/api/event')
        .then(response => {
          me = this
          this.events = response.data
        })
    },
    showModal(str) {
      this.errorMessage = str
      this.$refs.errorModal.show()
    }
  }
})
