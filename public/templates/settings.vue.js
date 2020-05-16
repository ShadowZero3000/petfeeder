Vue.component('settings', {
  data: function () {
    return {
      integrations: [],
      fields: [],
      errorString: ''
    }
  },
  methods: {
    getData() {
      axios
        .get('//'+window.location.host+'/api/integration')
        .then(response => {
          me = this
          this.integrations = response.data
        })
    },
    checkFormValidity() {
      const valid = event.srcElement.checkValidity()
      console.log(valid)
      return valid
    },
    handleIntegrationSubmit() {
      // Exit when the form isn't valid
      if (!this.checkFormValidity()) {
        return
      }
      console.log(event.submitter.value)
      this.submitIntegration(event.submitter.value, event.srcElement)
      // this.edit(this.editRow.item.id)
    },
    submitIntegration(integration_name, form){
      integration = _.find(this.integrations, ["name", integration_name])
      request = {}
      _.each(integration.details, (detail, key) => {
        request[key] = detail.value.toString()
        if(detail.type == "bool") {
          request[key] = detail.value
        }
      })
      axios
        .put('//'+window.location.host+'/api/integration/'+integration_name, request)
        .then(response => {
          me = this
          this.getData()
        })
        .catch(error => {
          this.errorString = "Request failed"
          this.errorString = error.response.data.status_details.description
        })

    }
  },
  mounted () {
    this.getData()
  },
  template: `
<template>
  <b-container-fluid>
    <div class="row">
      <div class="col col-sm-8"><h1>Settings</h1></div>
     <!--  <div class="col col-sm-2">
        <button class="btn btn-success btn-lg btn-block" role="button" @click="editorMode='Add'" v-b-modal.mealEditorModal>Add New</button>
      </div> -->
     <!--  <div class="col col-sm-2">
        <button class="btn btn-primary btn-lg btn-block" role="button" v-on:click="feed">Feed now</button>
      </div> -->
    </div>
    <div v-if="integrations.length > 0">
      <div v-for="integration in integrations" class="card" style="width: 25rem">
        <div class="card-body">
          <h5 class="card-title">{{_.startCase(integration.name)}}</h5>

          <form ref="EditorForm" @submit.stop.prevent="handleIntegrationSubmit" v-model="integration">
            <div class="alert alert-danger" v-if="errorString">{{errorString}}</div>
            <span v-for="detail,key in _.sortBy(integration.details, ['name'])">
              <b-form-group
                :state="detail.value"
                :label="detail.name"
                :label-for="detail.name+'-input'"
              >
                <b-form-checkbox
                  v-if="detail.type == 'bool'"
                  id="notify-checkbox"
                  v-model="detail.value"
                  :state="detail.value"
                  type="checkbox"
                />
                <b-form-input
                  v-else
                  :id="detail.name+'-input'"
                  v-model="detail.value"
                  :state="detail.value"
                  required
                  :aria-describedby="detail.name+'-description'"
                ></b-form-input>
                <small :id="detail.name+'-description'" class="text-muted">
                  {{ detail.description }}
                </small>
              </b-form-group>
            </span>
            <b-button type="submit" variant="primary" v-model="integration.name">Submit</b-button>
          </form>
        </div>
      </div>
    </div>
  </b-container-fluid>
</template>
`
})
