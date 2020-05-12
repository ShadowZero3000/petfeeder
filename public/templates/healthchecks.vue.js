Vue.component('healthchecks', {
  data: function () {
    return {
      events: [],
      fields: [
        {"label":"Name","key":"details.name"},
        {"label":"Time","key":"details.time"},
        {"label":"Check ID","key":"details.check_id"},
        {"label":"Notify","key":"notify"},
        {"label":"", "key":"details"}
      ],
      editorMode: null,
      editRow: null,
      healthCheckEditor: {
        "name": "",
        "time": "",
        "check_id": "",
        "notify": false
      },
      healthCheckEditorState: {},
      errorString: null
    }
  },
  methods: {
    getData() {
      axios
        .get('//'+window.location.host+'/api/event/healthcheck')
        .then(response => {
          me = this
          this.events = response.data
        })
    },
    remove(row) {
      console.log(row)
      axios
        .delete('//'+window.location.host+'/api/event/'+row.item.id)
        .then(response => {
          me = this
          this.getData()
        })
        .catch(error => {
          console.log("We should handle errors on delete")
        })
    },
    add() {
      axios
        .post('//'+window.location.host+'/api/event/healthCheck', this.healthCheckEditor)
        .then(response => {
          me = this
          this.getData()
          this.$nextTick(() => {
            this.$bvModal.hide('healthCheckEditorModal')
          })
        })
        .catch(error => {
          this.errorString = "Request failed"
          this.errorString = error.response.data.status_details.description
        })
    },
    edit(id) {
      axios
        .put('//'+window.location.host+'/api/event/healthCheck/'+id, this.healthCheckEditor)
        .then(response => {
          me = this
          this.getData()
          this.$nextTick(() => {
            this.$bvModal.hide('healthCheckEditorModal')
          })
        })
        .catch(error => {
          this.errorString = "Request failed"
          this.errorString = error.response.data.status_details.description
        })
    },
    checkFormValidity() {
      const valid = this.$refs.healthCheckEditorForm.checkValidity()
      this.healthCheckEditorState = valid
      return valid
    },
    am_pm_to_hours(time) {
        console.log(time);
        var hours = Number(time.match(/^(\d+)/)[1]);
        var minutes = Number(time.match(/:(\d+)/)[1]);
        var AMPM = time.match(/\s(.*)$/)[1];
        if (AMPM == "pm" && hours < 12) hours = hours + 12;
        if (AMPM == "am" && hours == 12) hours = hours - 12;
        var sHours = hours.toString();
        var sMinutes = minutes.toString();
        if (hours < 10) sHours = "0" + sHours;
        if (minutes < 10) sMinutes = "0" + sMinutes;
        return (sHours +':'+sMinutes);
    },
    loadModal() {
      this.resetModal()
      if(this.editorMode == "Edit") {
        this.healthCheckEditor = _.clone(this.editRow.item.details)
        this.healthCheckEditor.time = this.am_pm_to_hours(this.healthCheckEditor.time.toLowerCase())
      }
    },
    resetModal() {
      console.debug
      this.healthCheckEditor.name = ""
      this.healthCheckEditor.time = "7:00:00"
      this.healthCheckEditor.check_id = ""
      this.errorString = null
      this.healthCheckEditorState = {}
    },
    handleOk(bvModalEvt) {
      // Prevent modal from closing
      bvModalEvt.preventDefault()
      // Trigger submit handler
      this.handleSubmit()
    },
    handleSubmit() {
      // Exit when the form isn't valid
      if (!this.checkFormValidity()) {
        return
      }
      if(this.editorMode == "Add") {
        this.add()
      } else {
        this.edit(this.editRow.item.id)
      }
    }
  },
  mounted () {
    this.getData()
  },
  template: `
<template>
  <b-container-fluid>
    <div class="row">
      <div class="col col-sm-8"><h1>Health Check Schedule</h1></div>
      <div class="col col-sm-2">
        <button class="btn btn-success btn-lg btn-block" role="button" @click="editorMode='Add'" v-b-modal.healthCheckEditorModal>Add New</button>
      </div>
      <!-- <div class="col col-sm-2">
        <button class="btn btn-primary btn-lg btn-block" role="button" v-on:click="feed">Feed now</button>
      </div> -->
    </div>
    <div v-if="events.length > 0">
      <b-table striped :items="events" :fields="fields" >
        <template v-slot:cell(notify)="row">
          <div v-if="row.item.details.notify" class="far fa-comment" style="color:green"></div>
          <div v-else class="fa fa-comment-slash" style="color:red"></div>
        </template>
        <template v-slot:cell(details)="row">
            <button class="btn btn-secondary ml-auto" role="button" v-b-modal.healthCheckEditorModal @click="editorMode='Edit'; editRow=row">
              <div class="fa fa-edit"></div>
            </button>
            <button class="btn btn-danger ml-auto" role="button" v-on:click="remove(row)">
              <div class="fa fa-trash-alt"></div>
            </button>
        </template>
      </b-table>
    </div>
  <b-modal id="healthCheckEditorModal" :title="editorMode+' Health Check'"
      @show="loadModal"
      @hidden="resetModal"
      @ok="handleOk"
  >
    <form ref="healthCheckEditorForm" @submit.stop.prevent="handleSubmit">
      <div class="alert alert-danger" v-if="errorString">{{errorString}}</div>
        <b-form-group
          :state="healthCheckEditorState.name"
          label="Name"
          label-for="name-input"
          invalid-feedback="Name is required"
        >
          <b-form-input
            id="name-input"
            v-model="healthCheckEditor.name"
            :state="healthCheckEditorState.name"
            required
          ></b-form-input>
        </b-form-group>
        <b-form-group
          :state="healthCheckEditorState.time"
          label="Time"
          label-for="time-input"
          invalid-feedback="Time is required"
        >
          <b-time
            id="time-input"
            v-model="healthCheckEditor.time"
            :state="healthCheckEditorState.time"
            required
          ></b-time>
        </b-form-group>
        <b-form-group
          :state="healthCheckEditorState.check_id"
          label="Check ID"
          label-for="check_id-input"
          invalid-feedback="Check ID is required"
        >
          <b-form-input
            id="check_id-input"
            v-model="healthCheckEditor.check_id"
            :state="healthCheckEditorState.check_id"
            required
          ></b-form-input>
        </b-form-group>
        <b-form-group
          :state="healthCheckEditorState.notify"
          label="Notify on Telegram"
          label-for="notify-checkbox"
          invalid-feedback="notify is required"
        >
          <b-form-checkbox
            id="notify-checkbox"
            v-model="healthCheckEditor.notify"
            :state="healthCheckEditorState.notify"
            type="checkbox"
            required
          ></b-form-checkbox>
        </b-form-group>
    </form>
  </b-modal>
  </b-container-fluid>
</template>
`
})
